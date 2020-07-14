
import bpy
from math import sin, cos, pi, sqrt, atan2

from bpy_lattice import materials


def import_orbit(file):
    f = open(file, 'r')
    header1=f.readline()
    header2=f.readline()
    print(header1)
    orbit = [parse_orbit_line(line) for line in f]
    f.close()
    return orbit

def parse_orbit_line(line):
    """
    Returns coords in the Blender frame 
    """
    dat = line.split()
    #  0  1   2  3   4  5   6  7      8
    # (y, py, z, pz, x, px, t, e_tot, s_position)  = coords
    coords = [float(s) for s in dat[0:9] + dat[11:15] ]
    print(coords)
    return coords

    
def faces_from(sections, closed=True):
    """
    A section is a list of vertices that defines a cross-section of an element
    """
    nix = [len(s) for s in sections]
    if len(set(nix)) >1:
        print('ERROR: sections must have the same number of points')
        return
    n = nix[0]
    faces = []
    for i0 in range(len(sections) -1):
        for j in range(n-1):
            faces.append( (i0*n + j, (i0+1)*n +j, (i0+1)*n +j+1, i0*n +j+1) )
        faces.append((i0*n +n-1, (i0+1)*n +n-1, (i0+1)*n, i0*n))
    if closed:
        faces.append(range(n)) #first section
        faces.append(range((len(sections)-1)*n, (len(sections)-1)*n+n)) # Last section
    return faces  
    
    
def beam_sizes(coords, beam):
  beta_a, eta_x, beta_b, eta_y =  coords[9:13]
  e_tot = coords[7]
  mc2 = 0.511e6
  r1 = 10 * sqrt(beta_a * beam['emit_norm_a']*mc2/e_tot + eta_x**2 *  beam['sigma_delta']**2 )
  r2 = 10 * sqrt(beta_b * beam['emit_norm_b']*mc2/e_tot + eta_y**2 *  beam['sigma_delta']**2 )
  return r1, r2
    
def orbit_section(coords, rx, ry, n=30, beam=None):
    """ In the XY plane for now """
    y, py, z, pz, x, px, t, e_tot = coords[0:8]
    theta = atan2(py, px)
    angles = [2*pi*i/n for i in range(n)]
    if beam:
        r1, r2 = beam_sizes(coords, beam)
    else:
        r1 = rx
        r2 = ry
    
    return [(x - r1*cos(a)*sin(theta),y + r1*cos(a)*cos(theta),z + r2*sin(a)) for a in angles]
    #return [ (x + rx*cos(a)*cos(theta), y + ry*sin(a),  z + rx*cos(a)*sin(theta)) for a in angles]
    

def orbit_mesh(orbit, name, beam=None):
    rx = 0.012 # 12 mm
    ry  = 0.012
    sections = [orbit_section(coords, rx, ry, n=16, beam=beam) for coords in orbit]
    faces = faces_from(sections)
    verts = []
    for s in sections:
        for p in s:
            verts.append(p)
            
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    return mesh



ENERGY_COLOR = {42:(1,0,0), 78:(1,0.5,0), 114:(0,1,0), 150:(0,0,1), 6:(1,1,1)}


def orbit_color(orbit):
  coords = orbit[-1] 
  e_tot = int(coords[7]/1e6) # MeV
  if e_tot in ENERGY_COLOR:
    color = ENERGY_COLOR[e_tot]           
  else:
    color = (0.5, 0.5, 0.5)  
  return color

def orbit_name(orbit):
    # Name based on energy of last section
    coords = orbit[-1] 
    e_tot = int(coords[7]/1e6)
    if e_tot in ENERGY_COLOR:
        s = str(e_tot)
    else:
        s = 'changing'
    return 'energy_'+s+'_MeV'   

def orbit_material(orbit):
    name = orbit_name(orbit)+'_material'
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    return materials.diffuse_material(name, color=orbit_color(orbit)+tuple([1]))




def orbit_object(orbit, name:"test", beam=None):
    mesh = orbit_mesh(orbit, name, beam=beam)
    object = bpy.data.objects.new(name, mesh)
    bpy.context.scene.objects.link(object)
    object.location = (0, 0, 0) 
    
    mat = orbit_material(orbit)
    #print('color: ', color)
    mat.diffuse_color = orbit_color(orbit)
    object.data.materials.append(mat)            
    return object

    #bpy.context.scene.objects.link(object)

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]



###ROOT='/Users/cem52/accuser/linux_lib/test_floor_geometry/'
###file = ROOT+'global_orbit_with_ends.dat'
####file = ROOT+'global_orbit.dat'
###print('IMPORTING: ', file)
###orbit = import_orbit(file)    
###
###if __name__=='__main__':
###  orbs = chunks(orbit, 10) 
###    
###  ii = 1    
###  for o in orbs:
###    name = "sec_"+str(ii)
###    ob = orbit_object(o, name)
###    ii = ii + 1
### 
### 
