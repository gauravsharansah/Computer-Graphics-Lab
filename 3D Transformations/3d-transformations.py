import pygame
import math
import sys
pygame.init()
WIDTH,HEIGHT=800,600
screen=pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("3D Transformations")
WHITE=(255,255,255)
BLACK=(0,0,0)

def draw_line(x1,y1,x2,y2,color):
    dx=abs(x2-x1)
    dy=abs(y2-y1)
    if(x2>x1):
        lx=1
    else:
        lx=-1
    if(y2>y1):
        ly=1
    else:
        ly=-1
    
    x=x1
    y=y1
    if(dx>=dy):
        p=2*dy-dx
        for i in range(dx):
            screen.set_at((x,y), color)
            x+=lx
            if(p<0):
                p+=2*dy
            else:
                y+=ly
                p+=2*(dy-dx)
        screen.set_at((x,y), color)
    else:
        p=2*dx-dy
        for i in range(dy):
            screen.set_at((x,y), color)
            y+=ly
            if(p<0):
                p+=2*dx
            else:
                x+=lx
                p+=2*(dx-dy)
        screen.set_at((x,y), color)

def translate(vertices,tx,ty,tz):
    translated_vertices=[]
    for x,y,z in vertices:
        translated_vertices.append((x+tx,y+ty,z+tz))
    return translated_vertices

def scale(vertices,sx,sy,sz):
    scaled_vertices=[]
    for x,y,z in vertices:
        scaled_vertices.append((x*sx,y*sy,z*sz))
    return scaled_vertices

def reflect(vertices,axis):
    reflected_vertices=[]
    for x,y,z in vertices:
        if axis=='x':
            reflected_vertices.append((x,-y,-z))
        elif axis=='y':
            reflected_vertices.append((-x,y,-z))
        elif axis=='z':
            reflected_vertices.append((-x,-y,z))
        elif axis=='origin':
            reflected_vertices.append((-x,-y,-z))
    return reflected_vertices

def rotate(vertices,axis,angle,xr=0,yr=0,zr=0):
    rotated_vertices=[]
    rad=math.radians(angle)
    cos_theta=math.cos(rad)
    sin_theta=math.sin(rad)
    for x,y,z in vertices:
        if axis=='z':
            nx=int(cos_theta*(x-xr) - sin_theta*(y-yr) + xr)
            ny=int(sin_theta*(x-xr) + cos_theta*(y-yr) + yr)
            nz=z
        elif axis=='x':
            nx=x
            ny=int(cos_theta*(y-yr) - sin_theta*(z-zr) + yr)
            nz=int(sin_theta*(y-yr) + cos_theta*(z-zr) + zr)
        elif axis=='y':
            nx=int(cos_theta*(x-xr) - sin_theta*(z-zr) + xr)
            ny=y
            nz=int(sin_theta*(x-xr) + cos_theta*(z-zr) + zr)
        rotated_vertices.append((nx,ny,nz))
    return rotated_vertices

def projection(point,zr=800):
    x,y,z=point
    distance=zr
    factor=distance/(distance-z)
    x=x+WIDTH//2
    y=-y+HEIGHT//2
    return (int(x*factor),int(y*factor))

def draw_cube(vertices,edges,color):
    projected_points=[]
    for vertex in vertices:
        projected_points.append(projection(vertex))
    for edge in edges:
        start, end = edge
        x1,y1=projected_points[start]
        x2,y2=projected_points[end]
        draw_line(x1,y1,x2,y2,color)

def main():
    while True:
        for event in pygame.event.get():    
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill(WHITE)
        
        cube_vertices=[(-50,-50,-50),(-50,50,-50),(50,50,-50),(50,-50,-50),
          (-50,-50,50),(-50,50,50),(50,50,50),(50,-50,50)]

        cube_edges=[(0,1),(1,2),(2,3),(3,0),
            (4,5),(5,6),(6,7),(7,4),
            (0,4),(1,5),(2,6),(3,7)]
        translated=translate(cube_vertices,0,100,0)
        scaled=scale(cube_vertices,1.5,1.5,1.5)
        reflected = reflect(cube_vertices,'y')
        rotated = rotate(cube_vertices,'y',45)
        draw_cube(cube_vertices,cube_edges,BLACK) # Original Cube
        draw_cube(translated,cube_edges,"RED")  # Translated Cube
        draw_cube(scaled,cube_edges,"BLUE")  # Scaled Cube
        draw_cube(reflected,cube_edges,"GREEN")  # Reflected Cube
        draw_cube(rotated,cube_edges,"ORANGE")  # Rotated Cube
        pygame.display.flip()
if __name__ == "__main__":
    main()

