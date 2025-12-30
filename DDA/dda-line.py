import pygame
import sys
pygame.init()
WIDTH,HEIGHT=800,600
screen=pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("DDA Algorithm")
WHITE=(255,255,255)
BLACK=(0,0,0)

def draw_line_dda(x1,y1,x2,y2):
    dx=x2-x1
    dy=y2-y1
    m=dy/dx
    x=x1
    y=y1
    screen.set_at((round(x), round(y)), BLACK)
    if (dx >= dy):
        while (x < x2):
            x=x+1
            y=y+m
            screen.set_at((round(x), round(y)), BLACK)
    else:
        while (y <= y2):
            y=y+1
            x=x+(1/m)
            screen.set_at((round(x), round(y)), BLACK)

def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill(WHITE)
        draw_line_dda(20,20,100,100)
        pygame.display.flip()
if __name__ == "__main__":
    main()