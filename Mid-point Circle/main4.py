import pygame
import sys

pygame.init()
WIDTH,HEIGHT=1200,700
screen=pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("Mid-Point Circle Algorithm")
WHITE=(255,255,255)
BLACK=(0,0,0)
clock = pygame.time.Clock()

def mid_point_circle(x1, y1, r):
    x=0
    y=r
    p=1-r
    while x<=y:
        x+=1
        if p<0:
            p+=(2*x)+1
        else:
            y=y-1
            p=p+(2*x)-(2*y)+1
        
        pygame.display.update()
        pygame.time.delay(100)
        plot_points(x1,y1,x,y)

def plot_points(xc,yc,x,y):
    screen.set_at((xc + x, yc + y), "GREEN")
    screen.set_at((xc - x, yc + y), "BROWN")
    screen.set_at((xc + x, yc - y), "RED")
    screen.set_at((xc - x, yc - y), "ORANGE")
    screen.set_at((xc + y, yc + x), "YELLOW")
    screen.set_at((xc - y, yc + x), "PINK")
    screen.set_at((xc + y, yc - x), "BLUE")
    screen.set_at((xc - y, yc - x), "PURPLE")

    

def main():
    while True:
        for event in pygame.event.get():    
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill(WHITE)
        mid_point_circle(350,350,50)
        pygame.display.flip()
if __name__ == "__main__":
    main()

