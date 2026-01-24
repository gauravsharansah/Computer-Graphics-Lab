import pygame
import math
import sys
pygame.init()
WIDTH,HEIGHT=800,600
screen=pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("2D Transformations")
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
    
def translation(x1,y1,x2,y2,tx,ty):
    nx1=x1+tx
    ny1=y1+ty
    nx2=x2+tx
    ny2=y2+ty
    draw_line(nx1,ny1,nx2,ny2,"RED")

def scaling(x1,y1,x2,y2,sx,sy,xr,yr):
    nx1=int((x1-xr)*sx+xr)
    ny1=int((y1-yr)*sy+yr)
    nx2=int((x2-xr)*sx+xr)
    ny2=int((y2-yr)*sy+yr)
    draw_line(nx1,ny1,nx2,ny2,"BLUE")

def reflection(x1,y1,x2,y2,axis,xr,yr):
    if axis=='x':
        ny1=2*yr - y1
        ny2=2*yr - y2
        nx1=x1
        nx2=x2
    elif axis=='y':
        nx1=2*xr - x1
        nx2=2*xr - x2
        ny1=y1
        ny2=y2
    elif axis=='origin':
        nx1=2*xr - x1
        ny1=2*yr - y1
        nx2=2*xr - x2
        ny2=2*yr - y2
    draw_line(nx1,ny1,nx2,ny2,"ORANGE")

def rotation(x1,y1,x2,y2,angle,xr,yr):
    rad=math.radians(angle)
    cos_theta=math.cos(rad)
    sin_theta=math.sin(rad)
    nx1=int(cos_theta*(x1-xr) - sin_theta*(y1-yr) + xr)
    ny1=int(sin_theta*(x1-xr) + cos_theta*(y1-yr) + yr)
    nx2=int(cos_theta*(x2-xr) - sin_theta*(y2-yr) + xr)
    ny2=int(sin_theta*(x2-xr) + cos_theta*(y2-yr) + yr)
    draw_line(nx1,ny1,nx2,ny2,"GREEN")

def main():
    while True:
        for event in pygame.event.get():    
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill(WHITE)
        x1,y1,x2,y2=200,350,600,350
        draw_line(x1,y1,x2,y2,BLACK)  # Original Line
        translation(x1,y1,x2,y2,0,100)  # Translated Line
        scaling(x1,y1,x2,y2,1.5,1.5,400,300)  # Scaled Line
        reflection(x1,y1,x2,y2,'x',400,300)  # Reflected Line
        rotation(x1,y1,x2,y2,45,400,300)  # Rotated Line
        pygame.display.flip()
if __name__ == "__main__":
    main()

