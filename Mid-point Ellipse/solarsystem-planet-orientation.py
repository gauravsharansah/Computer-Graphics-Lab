import pygame
import sys

pygame.init()
WIDTH,HEIGHT=1200,700
screen=pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("Mid-Point Ellipse Algorithm")
WHITE=(255,255,255)
BLACK=(0,0,0)
clock = pygame.time.Clock()

def mid_point_ellipse(xc, yc, a, b):
    x=0
    y=b
    plot_points(xc,yc,x,y)
    p1=(b*b)-(a*a*b)+(0.25*a*a)
    while (2*b*b*x)<=(2*a*a*y):
        x+=1
        if p1<0:
            p1=p1+(2*b*b*x)+(b*b)   
        else:
            y=y-1
            p1=p1+(2*b*b*x)-(2*a*a*y)+(b*b)
        pygame.display.update()
        pygame.time.delay(10)
        plot_points(xc,yc,x,y)


    p2=(b*b*(x+0.5)**2)+(a*a*(y-1)**2)-(a*a*b*b)
    while y>=0:
        y-=1
        if p2>0:
            p2=p2-(2*a*a*y)+(a*a)
        else:
            x+=1
            p2=p2+(2*b*b*x)-(2*a*a*y)+(b*b)
        pygame.display.update()
        pygame.time.delay(10)
        plot_points(xc,yc,x,y)
    

def plot_points(xc,yc,x,y):
    screen.set_at((xc + x, yc + y), "GREEN")
    screen.set_at((xc - x, yc + y), "BROWN")
    screen.set_at((xc + x, yc - y), "RED")
    screen.set_at((xc - x, yc - y), "ORANGE")

    

def main():
    while True:
        for event in pygame.event.get():    
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill(WHITE)
        mid_point_ellipse(210,350,180,170)
        mid_point_ellipse(400,350,8,9)
        mid_point_ellipse(450,355,18,17)
        mid_point_ellipse(510,350,20,18)
        mid_point_ellipse(580,345,15,14)
        mid_point_ellipse(780,350,60,58)
        mid_point_ellipse(930,350,50,51)
        mid_point_ellipse(1050,350,40,39)
        mid_point_ellipse(1140,350,40,39)
        pygame.display.flip()
if __name__ == "__main__":
    main()

