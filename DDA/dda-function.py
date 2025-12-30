def DDA_Line(x1,y1,x2,y2):
    dx=x2-x1
    dy=y2-y1
    m=dy/dx
    x=x1
    y=y1
    print(f"({round(x)},{round(y)})")
    if (dx >= dy):
        while (x < x2):
            x=x+1
            y=y+m
            print(f"({round(x)},{round(y)})")
    else:
        while (y <= y2):
            y=y+1
            x=x+(1/m)
            print(f"({round(x)},{round(y)})")



x1,y1=map(int,input("Enter coordinates of source point: ").split())
x2,y2=map(int,input("Enter coordinates of destination point: ").split())
DDA_Line(x1,y1,x2,y2)
