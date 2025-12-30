import pygame
import sys
pygame.init()
WIDTH,HEIGHT=800,600
screen=pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("BLA Algorithm")
WHITE=(255,255,255)
BLACK=(0,0,0)

def draw_line_bla(x1,y1,x2,y2):
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
            screen.set_at((x,y), BLACK)
            x+=lx
            if(p<0):
                p+=2*dy
            else:
                y+=ly
                p+=2*(dy-dx)
        screen.set_at((x,y), BLACK)
    else:
        p=2*dx-dy
        for i in range(dy):
            screen.set_at((x,y), BLACK)
            y+=ly
            if(p<0):
                p+=2*dx
            else:
                x+=lx
                p+=2*(dx-dy)
        screen.set_at((x,y), BLACK)
    

def main():
    while True:
        for event in pygame.event.get():    
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill(WHITE)
        draw_line_bla(200,350,600,350)
        draw_line_bla(200,450,600,450)
        draw_line_bla(200,350,400,500)
        draw_line_bla(200,450,400,300)
        draw_line_bla(600,450,400,300)
        draw_line_bla(600,350,400,500)
        pygame.display.flip()
if __name__ == "__main__":
    main()

