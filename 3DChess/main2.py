import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import pywavefront
import os, sys, copy, json, datetime

# ==========================
# PATHS & BASE CONFIG
# ==========================
BASE_PATH  = os.path.join(os.path.dirname(__file__), "models")
SAVES_DIR  = os.path.join(os.path.dirname(__file__), "saves")
os.makedirs(SAVES_DIR, exist_ok=True)

WIDTH, HEIGHT  = 900, 650
BOARD_SIZE     = 8
SQUARE_SIZE    = 2.0
BOARD_HALF     = (BOARD_SIZE * SQUARE_SIZE) / 2.0   # 8.0

BOARD_OFFSET_X =  0.5
BOARD_OFFSET_Y =  2.0

board_color_theme = "black_white"

# Camera
camera_angle_x  = 35.0
camera_angle_y  = -30.0
camera_distance = 28.0
animation_speed = 0.18

# Piece values
PIECE_VALUES = {"pawn":1,"knight":3,"bishop":3,"rook":5,"queen":9,"king":0}

# Turn / state globals
current_turn     = "white"
in_check         = False
is_checkmate     = False
is_stalemate     = False
check_flash_t    = 0
game_over        = False
winner           = None
_pending_check_update = False

font_sm_global   = None


# ==========================
# PIECE CLASS
# ==========================
class Piece:
    def __init__(self, name, color, col, row):
        self.name  = name
        self.color = color
        self.col   = float(col)
        self.row   = float(row)
        self.model = None
        self._load_model()
        self.selected   = False
        self.animating  = False
        self.target_col = None
        self.target_row = None
        self.has_moved  = False

    def _load_model(self):
        path = os.path.join(BASE_PATH, f"{self.color}_{self.name}.obj")
        if os.path.exists(path):
            try:
                self.model = pywavefront.Wavefront(path, collect_faces=True)
                return
            except Exception as e:
                print(f"Warning: {path}: {e}")
        self.model = None

    def world_x(self):
        return (self.col - BOARD_SIZE/2.0)*SQUARE_SIZE + SQUARE_SIZE/2.0

    def world_z(self):
        return (self.row - BOARD_SIZE/2.0)*SQUARE_SIZE + SQUARE_SIZE/2.0

    def board_col(self): return int(round(self.col))
    def board_row(self): return int(round(self.row))

    def draw(self, flash_red=False):
        glPushMatrix()
        glTranslatef(self.world_x(), 0.0, self.world_z())
        if self.color == "white":
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR,  [1.0, 1.0, 0.98, 1.0])
            glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, 110.0)
        else:
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR,  [1.0, 0.90, 0.40, 1.0])
            glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, 72.0)

        if flash_red:
            glColor3f(1.0, 0.12, 0.12)
        elif self.selected:
            glColor3f(1.0, 0.88, 0.18)
        elif self.color == "white":
            glColor3f(0.98, 0.97, 0.93)
        else:
            glColor3f(0.05, 0.05, 0.05)

        if self.model:
            mat_data = []
            ax, ay, az = [], [], []
            for _, mesh in self.model.meshes.items():
                for mat in mesh.materials:
                    verts = mat.vertices
                    fmt   = mat.vertex_format
                    if   fmt=='V3F':         s,v=3,0
                    elif fmt=='T2F_V3F':     s,v=5,2
                    elif fmt=='N3F_V3F':     s,v=6,3
                    elif fmt=='T2F_N3F_V3F': s,v=8,5
                    else:                    s,v=3,0
                    mat_data.append((verts,s,v))
                    for i in range(0,len(verts),s):
                        ax.append(verts[i+v]); ay.append(verts[i+v+1]); az.append(verts[i+v+2])

            if ay:
                mnx,mxx=min(ax),max(ax); mny=min(ay); mnz,mxz=min(az),max(az)
                cxo=(mnx+mxx)/2.0; czo=(mnz+mxz)/2.0
                mw=mxx-mnx; md=mxz-mnz; mh=max(ay)-mny
                targets={
                    "pawn":  (0.78*1.35,1.05*1.35),
                    "rook":  (0.92*1.35,1.05*1.35),
                    "knight":(0.82*1.35,1.25*1.35),
                    "bishop":(0.78*1.35,1.40*1.35),
                    "queen": (0.88*1.35,1.58*1.35),
                    "king":  (0.88*1.35,1.72*1.35),
                }
                tb,th = targets.get(self.name,(0.82*1.35,1.20*1.35))
                hz = max(mw,md) if max(mw,md)>0 else 1.0
                sc = tb/hz
                if mh*sc>th and mh>0: sc=th/mh
                glTranslatef(-cxo*sc,-mny*sc,-czo*sc)
                glScalef(sc,sc,sc)

            for verts,s,v in mat_data:
                glBegin(GL_TRIANGLES)
                for i in range(0,len(verts),s):
                    glVertex3f(verts[i+v],verts[i+v+1],verts[i+v+2])
                glEnd()
        else:
            _draw_box(self.name)
        glPopMatrix()

    def start_move(self,nc,nr):
        self.target_col=float(nc); self.target_row=float(nr); self.animating=True

    def animate_step(self):
        if not self.animating: return
        dc=self.target_col-self.col; dr=self.target_row-self.row
        dist=(dc*dc+dr*dr)**0.5
        if dist<animation_speed:
            self.col=self.target_col; self.row=self.target_row
            self.animating=False; self.has_moved=True
        else:
            self.col+=dc/dist*animation_speed; self.row+=dr/dist*animation_speed

    def to_dict(self):
        return {"name":self.name,"color":self.color,"col":self.col,"row":self.row,"has_moved":self.has_moved}

    @staticmethod
    def from_dict(d):
        p=Piece(d["name"],d["color"],d["col"],d["row"])
        p.has_moved=d.get("has_moved",False)
        return p


def _draw_box(name):
    S=1.35
    sizes=dict(pawn=(0.39*S,1.05*S,0.39*S),rook=(0.46*S,1.05*S,0.46*S),
               knight=(0.41*S,1.25*S,0.41*S),bishop=(0.39*S,1.40*S,0.39*S),
               queen=(0.44*S,1.58*S,0.44*S),king=(0.44*S,1.72*S,0.44*S))
    hw,h,hd=sizes.get(name,(0.57*S,1.20*S,0.57*S))
    def quad(n,verts):
        glNormal3fv(n); glBegin(GL_QUADS)
        for v in verts: glVertex3fv(v)
        glEnd()
    quad((0,-1,0),[(-hw,0,-hd),(hw,0,-hd),(hw,0,hd),(-hw,0,hd)])
    quad((0, 1,0),[(-hw,h,-hd),(hw,h,-hd),(hw,h,hd),(-hw,h,hd)])
    quad((0,0, 1),[(-hw,0,hd),(hw,0,hd),(hw,h,hd),(-hw,h,hd)])
    quad((0,0,-1),[(-hw,0,-hd),(hw,0,-hd),(hw,h,-hd),(-hw,h,-hd)])
    quad((-1,0,0),[(-hw,0,-hd),(-hw,0,hd),(-hw,h,hd),(-hw,h,-hd)])
    quad((1,0,0),[(hw,0,-hd),(hw,0,hd),(hw,h,hd),(hw,h,-hd)])


# ==========================
# GAME STATE
# ==========================
pieces            = []
captured_by_white = []
captured_by_black = []
selected_piece    = None
move_history      = []
last_pawn_double  = None
promotion_active  = False
promotion_piece   = None
promotion_rects   = []


# ==========================
# BOARD HELPERS
# ==========================
def piece_at(col,row,pl=None):
    if pl is None: pl=pieces
    c,r=int(round(col)),int(round(row))
    for p in pl:
        if p.board_col()==c and p.board_row()==r: return p
    return None

def path_clear(c0,r0,c1,r1,pl=None):
    if pl is None: pl=pieces
    dc=c1-c0; dr=r1-r0; steps=max(abs(dc),abs(dr))
    if steps==0: return True
    sx=0 if dc==0 else dc//abs(dc); sy=0 if dr==0 else dr//abs(dr)
    for i in range(1,steps):
        if piece_at(c0+sx*i,r0+sy*i,pl): return False
    return True


# ==========================
# MOVE VALIDATION
# ==========================
def _raw_valid(piece,tc,tr,pl,ep=None):
    sc,sr=piece.board_col(),piece.board_row(); dc,dr=tc-sc,tr-sr
    if dc==0 and dr==0: return False
    if not(0<=tc<8 and 0<=tr<8): return False
    tgt=piece_at(tc,tr,pl)
    if tgt and tgt.color==piece.color: return False
    n=piece.name
    if n=="pawn":
        d=1 if piece.color=="white" else -1; sr0=1 if piece.color=="white" else 6
        if dc==0 and dr==d:   return piece_at(tc,tr,pl) is None
        if dc==0 and dr==2*d and sr==sr0:
            return piece_at(sc,sr+d,pl) is None and piece_at(tc,tr,pl) is None
        if abs(dc)==1 and dr==d:
            if tgt and tgt.color!=piece.color: return True
            if ep and ep.board_col()==tc and ep.board_row()==sr: return True
        return False
    elif n=="rook":   return (dc==0 or dr==0) and path_clear(sc,sr,tc,tr,pl)
    elif n=="bishop": return abs(dc)==abs(dr) and path_clear(sc,sr,tc,tr,pl)
    elif n=="queen":  return (dc==0 or dr==0 or abs(dc)==abs(dr)) and path_clear(sc,sr,tc,tr,pl)
    elif n=="knight": return (abs(dc),abs(dr)) in [(1,2),(2,1)]
    elif n=="king":
        if max(abs(dc),abs(dr))==1: return True
        if not piece.has_moved and dr==0 and abs(dc)==2:
            rc=0 if dc<0 else 7; rk=piece_at(rc,sr,pl)
            if rk and rk.name=="rook" and not rk.has_moved:
                step=1 if dc>0 else -1
                for x in range(sc+step,rc,step):
                    if piece_at(x,sr,pl): return False
                return True
        return False
    return False

def _find_king(color,pl):
    for p in pl:
        if p.name=="king" and p.color==color: return p
    return None

def _king_in_check(color,pl):
    king=_find_king(color,pl)
    if not king: return False
    opp="black" if color=="white" else "white"
    for p in pl:
        if p.color!=opp: continue
        if _raw_valid(p,king.board_col(),king.board_row(),pl): return True
    return False

def _simulate(piece,tc,tr,ep):
    sim=[copy.copy(p) for p in pieces]
    idx=pieces.index(piece); sp=sim[idx]
    sc,sr=sp.board_col(),sp.board_row(); dc,dr=tc-sc,tr-sr
    if sp.name=="pawn" and abs(dc)==1 and piece_at(tc,tr,sim) is None and ep:
        ep_s=next((p for p in sim if p.board_col()==ep.board_col() and p.board_row()==ep.board_row()),None)
        if ep_s: sim.remove(ep_s)
    if sp.name=="king" and abs(dc)==2:
        rc=0 if dc<0 else 7; rk=piece_at(rc,sr,sim)
        if rk: rk.col=float(sc-1 if dc<0 else sc+1)
    tgt=piece_at(tc,tr,sim)
    if tgt: sim.remove(tgt)
    sp.col=float(tc); sp.row=float(tr); sp.has_moved=True
    return sim

def is_valid_move(piece,tc,tr):
    if not _raw_valid(piece,tc,tr,pieces,ep=last_pawn_double): return False
    sim=_simulate(piece,tc,tr,last_pawn_double)
    return not _king_in_check(piece.color,sim)

def has_any_legal_move(color):
    for p in pieces:
        if p.color!=color: continue
        for tc in range(8):
            for tr in range(8):
                if is_valid_move(p,tc,tr): return True
    return False


# ==========================
# EXECUTE MOVE
# ==========================
def execute_move(piece,tc,tr):
    global last_pawn_double,promotion_active,promotion_piece,current_turn
    global captured_by_white,captured_by_black,game_over,winner
    global in_check,is_checkmate,is_stalemate,check_flash_t,_pending_check_update

    if not is_valid_move(piece,tc,tr): return False
    sc,sr=piece.board_col(),piece.board_row(); dc,dr=tc-sc,tr-sr

    if piece.name=="pawn" and abs(dc)==1 and piece_at(tc,tr) is None:
        ep=last_pawn_double
        if ep and ep.board_col()==tc and ep.board_row()==sr:
            (captured_by_white if piece.color=="white" else captured_by_black).append(ep.name)
            pieces.remove(ep)

    last_pawn_double=piece if(piece.name=="pawn" and abs(dr)==2) else None

    if piece.name=="king" and abs(dc)==2:
        rc=0 if dc<0 else 7; rk=piece_at(rc,sr)
        if rk: rk.start_move(sc-1 if dc<0 else sc+1,sr)

    tgt=piece_at(tc,tr)
    if tgt:
        (captured_by_white if piece.color=="white" else captured_by_black).append(tgt.name)
        pieces.remove(tgt)

    files="hgfedcba"; sym={"pawn":"","rook":"R","knight":"N","bishop":"B","queen":"Q","king":"K"}
    move_history.append({"piece":piece.name,"color":piece.color,
        "from":(sc,sr),"to":(tc,tr),
        "label":f"{sym[piece.name]}{files[sc]}{sr+1}{files[tc]}{tr+1}"})

    piece.start_move(tc,tr)

    promo_row=7 if piece.color=="white" else 0
    if piece.name=="pawn" and tr==promo_row:
        promotion_active=True; promotion_piece=piece
    else:
        current_turn="black" if current_turn=="white" else "white"
        _pending_check_update = True
    return True

def _update_check_state():
    global in_check,is_checkmate,is_stalemate,check_flash_t,game_over,winner
    in_check=_king_in_check(current_turn,pieces)
    if in_check: check_flash_t=90
    has_moves=has_any_legal_move(current_turn)
    is_checkmate=in_check and not has_moves
    is_stalemate=(not in_check) and (not has_moves)
    if is_checkmate:
        game_over=True; winner="black" if current_turn=="white" else "white"
    elif is_stalemate:
        game_over=True; winner="draw"


# ==========================
# SAVE / LOAD
# ==========================
def save_game(slot=None):
    ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname=f"game_{ts}.json" if slot is None else f"slot_{slot}.json"
    path=os.path.join(SAVES_DIR,fname)
    data={
        "current_turn":current_turn,
        "pieces":[p.to_dict() for p in pieces],
        "captured_by_white":captured_by_white,
        "captured_by_black":captured_by_black,
        "move_history":move_history,
        "last_pawn_double": None if last_pawn_double is None else last_pawn_double.to_dict(),
    }
    with open(path,"w") as f: json.dump(data,f,indent=2)
    return fname

def load_game(fname):
    global pieces,current_turn,captured_by_white,captured_by_black
    global move_history,last_pawn_double,selected_piece
    global in_check,is_checkmate,is_stalemate,check_flash_t,game_over,winner
    global promotion_active,promotion_piece,_pending_check_update
    path=os.path.join(SAVES_DIR,fname)
    if not os.path.exists(path): return False
    with open(path) as f: data=json.load(f)
    pieces=[Piece.from_dict(d) for d in data["pieces"]]
    current_turn=data["current_turn"]
    captured_by_white=data["captured_by_white"]
    captured_by_black=data["captured_by_black"]
    move_history=data["move_history"]
    lpd=data.get("last_pawn_double")
    last_pawn_double=Piece.from_dict(lpd) if lpd else None
    selected_piece=None; promotion_active=False; promotion_piece=None
    in_check=False; is_checkmate=False; is_stalemate=False
    check_flash_t=0; game_over=False; winner=None; _pending_check_update=False
    _update_check_state()
    return True

def list_saves():
    saves=sorted([f for f in os.listdir(SAVES_DIR) if f.endswith(".json")],reverse=True)
    return saves[:8]


# ==========================
# INIT PIECES
# ==========================
def initialize_pieces():
    global pieces,selected_piece,move_history,last_pawn_double
    global promotion_active,promotion_piece,current_turn
    global captured_by_white,captured_by_black
    global in_check,is_checkmate,is_stalemate,check_flash_t,game_over,winner
    global _pending_check_update
    pieces=[];selected_piece=None;move_history=[];last_pawn_double=None
    promotion_active=False;promotion_piece=None;current_turn="white"
    captured_by_white=[];captured_by_black=[]
    in_check=False;is_checkmate=False;is_stalemate=False
    check_flash_t=0;game_over=False;winner=None;_pending_check_update=False
    
    # Files h→a (col 0=h, col 7=a) so e1 (col 3) is DARK
    pieces.append(Piece("rook",   "white", 0, 0))  # h1
    pieces.append(Piece("knight", "white", 1, 0))  # g1
    pieces.append(Piece("bishop", "white", 2, 0))  # f1
    pieces.append(Piece("king",   "white", 3, 0))  # e1 (DARK)
    pieces.append(Piece("queen",  "white", 4, 0))  # d1
    pieces.append(Piece("bishop", "white", 5, 0))  # c1
    pieces.append(Piece("knight", "white", 6, 0))  # b1
    pieces.append(Piece("rook",   "white", 7, 0))  # a1
    for col in range(8):
        pieces.append(Piece("pawn", "white", col, 1))
    
    pieces.append(Piece("rook",   "black", 0, 7))  # h8
    pieces.append(Piece("knight", "black", 1, 7))  # g8
    pieces.append(Piece("bishop", "black", 2, 7))  # f8
    pieces.append(Piece("king",   "black", 3, 7))  # e8 (DARK)
    pieces.append(Piece("queen",  "black", 4, 7))  # d8
    pieces.append(Piece("bishop", "black", 5, 7))  # c8
    pieces.append(Piece("knight", "black", 6, 7))  # b8
    pieces.append(Piece("rook",   "black", 7, 7))  # a8
    for col in range(8):
        pieces.append(Piece("pawn", "black", col, 6))

initialize_pieces()


# ==========================
# OPENGL INIT
# ==========================
def init_opengl():
    glEnable(GL_DEPTH_TEST); glDepthFunc(GL_LEQUAL)
    glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_LIGHT1)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK,GL_AMBIENT_AND_DIFFUSE)
    glEnable(GL_NORMALIZE)
    glLightfv(GL_LIGHT0, GL_POSITION, [10.0, 22.0,  12.0, 0.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0,  0.96,  0.88, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0,  1.0,   1.0,  1.0])
    glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.22, 0.20,  0.16, 1.0])
    glLightfv(GL_LIGHT1, GL_POSITION, [-12.0, 14.0, -8.0, 0.0])
    glLightfv(GL_LIGHT1, GL_DIFFUSE,  [0.32,  0.36, 0.45, 1.0])
    glLightfv(GL_LIGHT1, GL_SPECULAR, [0.20,  0.22, 0.30, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR,  [0.9, 0.9, 0.85, 1.0])
    glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, 80.0)
    glClearColor(0.10, 0.07, 0.04, 1.0)
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(45,WIDTH/HEIGHT,0.1,200)
    glMatrixMode(GL_MODELVIEW)


def set_camera():
    glLoadIdentity()
    glTranslatef(BOARD_OFFSET_X, BOARD_OFFSET_Y,-camera_distance)
    glRotatef(camera_angle_x,1,0,0)
    glRotatef(camera_angle_y,0,1,0)


# ==========================
# DRAW BOARD
# ==========================
def draw_board():
    glDisable(GL_LIGHTING)
    for col in range(BOARD_SIZE):
        for row in range(BOARD_SIZE):
            if board_color_theme=="dark_blue":
                light,dark=(0.75,0.85,0.95),(0.10,0.20,0.45)
            else:
                light,dark=(0.94,0.88,0.70),(0.32,0.18,0.06)
            color=light if(col+row)%2==0 else dark
            if selected_piece and selected_piece.board_col()==col and selected_piece.board_row()==row:
                color=(0.85,0.85,0.10)
            glColor3fv(color)
            x0=(col-BOARD_SIZE/2)*SQUARE_SIZE; z0=(row-BOARD_SIZE/2)*SQUARE_SIZE
            glBegin(GL_QUADS); glNormal3f(0,1,0)
            glVertex3f(x0,0,z0); glVertex3f(x0+SQUARE_SIZE,0,z0)
            glVertex3f(x0+SQUARE_SIZE,0,z0+SQUARE_SIZE); glVertex3f(x0,0,z0+SQUARE_SIZE)
            glEnd()
    bw=0.5; H=BOARD_HALF
    glColor3f(0.35,0.20,0.05); glBegin(GL_QUADS)
    glVertex3f(-H-bw,-0.05,-H-bw); glVertex3f(H+bw,-0.05,-H-bw); glVertex3f(H+bw,-0.05,-H);    glVertex3f(-H-bw,-0.05,-H)
    glVertex3f(-H-bw,-0.05, H);    glVertex3f(H+bw,-0.05, H);    glVertex3f(H+bw,-0.05, H+bw); glVertex3f(-H-bw,-0.05, H+bw)
    glVertex3f(-H-bw,-0.05,-H-bw); glVertex3f(-H,  -0.05,-H-bw); glVertex3f(-H,  -0.05, H+bw); glVertex3f(-H-bw,-0.05, H+bw)
    glVertex3f( H,   -0.05,-H-bw); glVertex3f(H+bw,-0.05,-H-bw); glVertex3f(H+bw,-0.05, H+bw); glVertex3f( H,   -0.05, H+bw)
    glEnd(); glEnable(GL_LIGHTING)

def draw_shadows():
    glDisable(GL_LIGHTING); glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA); glColor4f(0,0,0,0.35)
    r=SQUARE_SIZE*0.36
    for p in pieces:
        wx,wz=p.world_x(),p.world_z()
        glBegin(GL_TRIANGLE_FAN); glVertex3f(wx,0.01,wz)
        for i in range(17): a=2*np.pi*i/16; glVertex3f(wx+r*np.cos(a),0.01,wz+r*np.sin(a))
        glEnd()
    glDisable(GL_BLEND); glEnable(GL_LIGHTING)

def draw_move_highlights():
    if not selected_piece: return
    glDisable(GL_LIGHTING); glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
    for col in range(8):
        for row in range(8):
            if is_valid_move(selected_piece,col,row):
                tgt=piece_at(col,row)
                glColor4f(0.9,0.2,0.2,0.5) if tgt else glColor4f(0.2,0.9,0.2,0.38)
                pad=0.12; x0=(col-BOARD_SIZE/2)*SQUARE_SIZE+pad; z0=(row-BOARD_SIZE/2)*SQUARE_SIZE+pad
                glBegin(GL_QUADS)
                glVertex3f(x0,0.03,z0); glVertex3f(x0+SQUARE_SIZE-2*pad,0.03,z0)
                glVertex3f(x0+SQUARE_SIZE-2*pad,0.03,z0+SQUARE_SIZE-2*pad); glVertex3f(x0,0.03,z0+SQUARE_SIZE-2*pad)
                glEnd()
    glDisable(GL_BLEND); glEnable(GL_LIGHTING)

def mouse_to_board(mx,my):
    vp=glGetIntegerv(GL_VIEWPORT); mv=glGetDoublev(GL_MODELVIEW_MATRIX); pr=glGetDoublev(GL_PROJECTION_MATRIX)
    wy=vp[3]-my
    try:
        nx,ny,nz=gluUnProject(mx,wy,0,mv,pr,vp); fx,fy,fz=gluUnProject(mx,wy,1,mv,pr,vp)
    except: return None
    dy=fy-ny
    if abs(dy)<1e-9: return None
    t=-ny/dy
    if t<0: return None
    hx=nx+t*(fx-nx); hz=nz+t*(fz-nz)
    col=int((hx+BOARD_HALF)/SQUARE_SIZE); row=int((hz+BOARD_HALF)/SQUARE_SIZE)
    return(col,row) if(0<=col<8 and 0<=row<8) else None


# ==========================
# MATERIAL / ADVANTAGE
# ==========================
# def _material_advantage():
#     white_captured_val = sum(PIECE_VALUES.get(n,0) for n in captured_by_white)
#     black_captured_val = sum(PIECE_VALUES.get(n,0) for n in captured_by_black)
#     diff = white_captured_val - black_captured_val
#     if diff > 0:   return "white", diff
#     elif diff < 0: return "black", -diff
#     else:          return None, 0


def _material_advantage():
    white_val = 0
    black_val = 0

    for p in pieces:
        value = PIECE_VALUES.get(p.name, 0)
        if p.color == "white":
            white_val += value
        else:
            black_val += value

    diff = white_val - black_val

    if diff > 0:
        return "white", diff
    elif diff < 0:
        return "black", -diff
    else:
        return None, 0


# ==========================
# CHESS.COM-STYLE CAPTURED PANEL
# ==========================
PANEL_X=WIDTH-185; STRIP_W=175; SYM_SIZE=13; SYM_PAD=2

def draw_chesscom_captured(surface, font_xs, font_sm, font_md):
    SYMS={"pawn":"♟","rook":"♜","bishop":"♝","knight":"♞","queen":"♛"}
    ORDER=["queen","rook","bishop","knight","pawn"]
    adv_color, adv_amt = _material_advantage()
    def count(lst):
        c={}
        for n in lst: c[n]=c.get(n,0)+1
        return c
    def render_strip(surface, captured_list, strip_y, strip_h,
                     player_label, player_col, adv_for_this_player):
        pygame.draw.rect(surface,(18,18,28,190),(PANEL_X, strip_y, STRIP_W, strip_h),border_radius=6)
        pygame.draw.rect(surface,(80,70,40,160),(PANEL_X, strip_y, STRIP_W, strip_h),1,border_radius=6)
        pl_img = font_sm.render(player_label, True, player_col)
        surface.blit(pl_img,(PANEL_X+8, strip_y+4))
        cx=PANEL_X+8; cy=strip_y+24
        counts = count(captured_list)
        for pname in ORDER:
            cnt = counts.get(pname,0)
            if cnt==0: continue
            for _ in range(cnt):
                pi = font_xs.render(SYMS.get(pname,"?"), True, player_col)
                surface.blit(pi,(cx,cy)); cx+=pi.get_width()+SYM_PAD
                if cx > PANEL_X+STRIP_W-18:
                    cx=PANEL_X+8; cy+=pi.get_height()+2
        if adv_for_this_player and adv_amt>0:
            badge = font_sm.render(f"+{adv_amt}", True,(220,220,100))
            bx=cx+6; by=cy+2
            if bx+badge.get_width()+6 > PANEL_X+STRIP_W:
                bx=PANEL_X+8; by=cy+font_xs.get_height()+4
            surface.blit(badge,(bx,by))
    top_y=55; strip_h=68
    render_strip(surface, captured_by_black, top_y, strip_h,
                 "Black", (200,200,200),
                 adv_for_this_player=(adv_color=="black"))
    bot_y = HEIGHT - strip_h - 55
    render_strip(surface, captured_by_white, bot_y, strip_h,
                 "White", (255,255,255),
                 adv_for_this_player=(adv_color=="white"))


# ==========================
# GAME-OVER SCREEN (FIXED HEIGHT)
# ==========================
gameover_rects = {}
def draw_gameover_screen(surface, font_sm, font_md, font_lg):
    global gameover_rects
    gameover_rects={}
    ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    ov.fill((0,0,0,160)); surface.blit(ov,(0,0))
    
    # FIXED: Increased height from 240 → 280 for better spacing
    bw,bh=420,340; bx=(WIDTH-bw)//2; by=(HEIGHT-bh)//2
    pygame.draw.rect(surface,(18,20,35,245),(bx,by,bw,bh),border_radius=14)
    pygame.draw.rect(surface,(200,180,50,255),(bx,by,bw,bh),2,border_radius=14)
    
    if winner=="draw":
        title_txt="Draw  —  Stalemate"; title_col=(220,210,100)
        bar_col=(60,60,20,230)
    elif winner=="white":
        title_txt="WHITE  WINS!"; title_col=(255,255,220)
        bar_col=(40,40,40,240)
    else:
        title_txt="YELLOW  WINS!"; title_col=(255,220,30)
        bar_col=(40,30,5,240)
    
    pygame.draw.rect(surface,bar_col,(bx+2,by+2,bw-4,72),border_radius=12)
    font_xl=pygame.font.SysFont("segoeui",34,bold=True)
    ti=font_xl.render(title_txt,True,title_col)
    surface.blit(ti,(bx+(bw-ti.get_width())//2, by+20))
    
    sub_txt="by Checkmate" if (winner and winner!="draw") else ""
    if sub_txt:
        si=font_md.render(sub_txt,True,(200,195,180))
        surface.blit(si,(bx+(bw-si.get_width())//2, by+70))
    
    mc_txt=f"{len(move_history)} moves played"
    mc=font_sm.render(mc_txt,True,(160,160,160))
    surface.blit(mc,(bx+(bw-mc.get_width())//2, by+108))
    
    BTN_W,BTN_H=170,42; gap=20
    total_btn_w=BTN_W*2+gap; start_bx=bx+(bw-total_btn_w)//2
    def btn(label,key,rx,ry,hot_col=(60,120,200)):
        r=pygame.Rect(rx,ry,BTN_W,BTN_H)
        pygame.draw.rect(surface,hot_col,r,border_radius=8)
        pygame.draw.rect(surface,(200,180,50),r,1,border_radius=8)
        img=font_md.render(label,True,(240,240,240))
        surface.blit(img,(rx+(BTN_W-img.get_width())//2,ry+(BTN_H-img.get_height())//2))
        gameover_rects[key]=r
    
    # FIXED: Moved buttons lower with more spacing
    btn_y=by+168
    btn("New Game",      "new",   start_bx,          btn_y, (50,130,80))
    btn("Save & Quit",   "saveq", start_bx+BTN_W+gap, btn_y, (130,80,50))
    btn2_y=btn_y+BTN_H+16
    btn("Load Game",     "load",  start_bx,          btn2_y,(80,80,160))
    btn("Quit App",      "quit",  start_bx+BTN_W+gap, btn2_y,(140,40,40))


# ==========================
# LOAD GAME MENU
# ==========================
load_menu_active=False
load_menu_rects={}
def draw_load_menu(surface,font_sm,font_md):
    global load_menu_rects
    load_menu_rects={}
    saves=list_saves()
    bw=420; bh=min(60+len(saves)*38+50,420); bx=(WIDTH-bw)//2; by=(HEIGHT-bh)//2
    pygame.draw.rect(surface,(18,20,35,245),(bx,by,bw,bh),border_radius=12)
    pygame.draw.rect(surface,(200,180,50,255),(bx,by,bw,bh),2,border_radius=12)
    t=font_md.render("Load Saved Game",True,(220,200,80))
    surface.blit(t,(bx+(bw-t.get_width())//2,by+12))
    if not saves:
        ni=font_sm.render("No saved games found.",True,(180,180,180))
        surface.blit(ni,(bx+(bw-ni.get_width())//2,by+52))
    for i,fname in enumerate(saves):
        ry=by+52+i*38
        r=pygame.Rect(bx+20,ry,bw-40,32)
        pygame.draw.rect(surface,(40,45,70),r,border_radius=6)
        pygame.draw.rect(surface,(100,90,50),r,1,border_radius=6)
        label=fname.replace(".json","").replace("_"," ")
        li=font_sm.render(label,True,(210,210,210))
        surface.blit(li,(r.x+8,r.y+7))
        load_menu_rects[fname]=r
    cy=by+bh-42; cr=pygame.Rect(bx+(bw-120)//2,cy,120,32)
    pygame.draw.rect(surface,(100,40,40),cr,border_radius=6)
    xi=font_sm.render("Cancel",True,(240,240,240))
    surface.blit(xi,(cr.x+(120-xi.get_width())//2,cr.y+7))
    load_menu_rects["__cancel__"]=cr


# ==========================
# 2-D OVERLAY (FIXED MOVE HISTORY HEIGHT CALCULATION)
# ==========================
def draw_overlay(surface, font_xs, font_sm, font_md, font_lg):
    surface.fill((0,0,0,0))

    # ── Move history (FIXED: proper height calculation) ───────────────────
    hist_w = 260
    white_moves = [m for m in move_history if m["color"]=="white"]
    black_moves = [m for m in move_history if m["color"]=="black"]
    max_rows = max(len(white_moves), len(black_moves), 1)
    
    # FIXED: Added extra padding (68 instead of 48) to prevent text cutoff
    hist_h = max(max_rows * 20 + 70, 130)
    
    pygame.draw.rect(surface,(0,0,0,170),(5,5,hist_w,hist_h),border_radius=8)
    pygame.draw.rect(surface,(200,180,50,130),(5,5,hist_w,hist_h),1,border_radius=8)
    lbl=font_md.render("Move History",True,(220,200,80))
    surface.blit(lbl,(12,10))
    pygame.draw.line(surface,(180,160,50),(12,32),(hist_w-8,32),1)
    
    # Column headers
    wh=font_sm.render("White",True,(230,230,230))
    bh=font_sm.render("Black",True,(160,160,255))
    surface.blit(wh,(22,36))
    surface.blit(bh,(190,36))
    
    # Draw moves
    y_start = 56
    for i, entry in enumerate(white_moves[-20:]):
        y = y_start + i * 20
        surface.blit(font_sm.render(entry["label"],True,(230,230,230)),(22,y))
    for i, entry in enumerate(black_moves[-20:]):
        y = y_start + i * 20
        surface.blit(font_sm.render(entry["label"],True,(160,160,255)),(190,y))

    # ── Turn indicator ─────────────────────────────────────────────────────
    if not game_over:
        tt="White's Turn" if current_turn=="white" else "Black's Turn"
        bg=(230,230,230,215) if current_turn=="white" else(30,30,30,215)
        fg=(10,10,10) if current_turn=="white" else(230,230,230)
        tw,th_=160,34; tx=WIDTH-tw-195
        pygame.draw.rect(surface,bg,(tx,8,tw,th_),border_radius=7)
        pygame.draw.rect(surface,(200,180,50,200),(tx,8,tw,th_),2,border_radius=7)
        ti=font_md.render(tt,True,fg); surface.blit(ti,(tx+(tw-ti.get_width())//2,8+(th_-ti.get_height())//2))

    # ── CHECK banner ───────────────────────────────────────────────────────
    if in_check and not game_over:
        ci=font_md.render("CHECK!",True,(255,100,100)); cx=(WIDTH-ci.get_width())//2
        pygame.draw.rect(surface,(80,0,0,200),(cx-10,8,ci.get_width()+20,34),border_radius=7)
        surface.blit(ci,(cx,12))

    # ── Controls panel ─────────────────────────────────────────────────────
    col1=[
        ("── Mouse ──",True,""),
        ("Left-click piece",False,"Select piece"),
        ("Left-click square",False,"Move / capture"),
        ("Left-drag",False,"Orbit camera"),
        ("Scroll wheel",False,"Zoom in/out"),
    ]
    col2=[
        ("── Keys ──",True,""),
        ("Arrow ← →",False,"Rotate L/R"),
        ("Arrow ↑ ↓",False,"Tilt up/down"),
        ("Z / X",False,"Zoom in/out"),
        ("M",False,"Board theme"),
        ("S",False,"Save game (slot 1)"),
        ("L",False,"Load game menu"),
        ("N",False,"New game"),
        ("Q",False,"Quit to menu"),
        ("R",False,"Hard reset"),
        ("Esc",False,"Deselect"),
    ]
    rh=17; pad=8; cw=240
    rows=max(len(col1),len(col2))
    ph=rows*rh+pad*2+6; py=HEIGHT-ph-5; pw=cw*2+20
    pygame.draw.rect(surface,(0,0,0,170),(5,py,pw,ph),border_radius=8)
    pygame.draw.rect(surface,(200,180,50,100),(5,py,pw,ph),1,border_radius=8)
    for ci_,col_lines in enumerate((col1,col2)):
        px2=14+ci_*(cw+4); cy2=py+pad
        for item in col_lines:
            hd=item[1]; kt=item[0]; dt=item[2] if len(item)>2 else ""
            kc=(220,200,80) if hd else(180,220,255)
            surface.blit(font_sm.render(kt,True,kc),(px2,cy2))
            if not hd and dt:
                surface.blit(font_sm.render(dt,True,(200,200,200)),(px2+105,cy2))
            cy2+=rh

    # ── Captured pieces panel ──────────────────────────────────────────────
    draw_chesscom_captured(surface, font_xs, font_sm, font_md)

    # ── BOARD COORDINATES (h→a, 1-8) ───────────────────────────────────────
    viewport   = glGetIntegerv(GL_VIEWPORT)
    modelview  = glGetDoublev(GL_MODELVIEW_MATRIX)
    projection = glGetDoublev(GL_PROJECTION_MATRIX)
    
    coord_font = pygame.font.SysFont("segoeuisymbol", 14, bold=True)
    files = "hgfedcba"
    ranks = "12345678"
    
    for col in range(8):
        wx = (col - BOARD_SIZE/2.0 + 0.5)*SQUARE_SIZE
        wz = -BOARD_HALF - 0.3
        try:
            sx, sy, _ = gluProject(wx, 0.0, wz, modelview, projection, viewport)
            sy = viewport[3] - sy
            is_light = (col) % 2 == 0
            txt_col = (40,30,15) if is_light else (220,200,150)
            lbl = coord_font.render(files[col], True, txt_col)
            surface.blit(lbl, (int(sx - lbl.get_width()//2), int(sy - lbl.get_height()//2)))
        except: pass
    
    for row in range(8):
        wx = -BOARD_HALF - 0.3
        wz = (row - BOARD_SIZE/2.0 + 0.5)*SQUARE_SIZE
        try:
            sx, sy, _ = gluProject(wx, 0.0, wz, modelview, projection, viewport)
            sy = viewport[3] - sy
            is_light = (row) % 2 == 0
            txt_col = (40,30,15) if is_light else (220,200,150)
            lbl = coord_font.render(ranks[row], True, txt_col)
            surface.blit(lbl, (int(sx - lbl.get_width()//2), int(sy - lbl.get_height()//2)))
        except: pass

    # ── Game over / load menus ─────────────────────────────────────────────
    if game_over:
        draw_gameover_screen(surface, font_sm, font_md, font_lg)
    if load_menu_active:
        draw_load_menu(surface, font_sm, font_md)


# ==========================
# PROMOTION MENU
# ==========================
def draw_promotion_menu(surface, font_md, font_lg):
    global promotion_rects, font_sm_global
    promotion_rects=[]
    choices=["queen","rook","bishop","knight"]
    syms={"queen":"♛","rook":"♜","bishop":"♝","knight":"♞"}
    bw,bh=360,130; bx=(WIDTH-bw)//2; by=(HEIGHT-bh)//2
    pygame.draw.rect(surface,(25,25,40,230),(bx,by,bw,bh),border_radius=10)
    pygame.draw.rect(surface,(200,180,50,255),(bx,by,bw,bh),2,border_radius=10)
    t=font_md.render("Promote pawn to:",True,(220,200,80))
    surface.blit(t,(bx+(bw-t.get_width())//2,by+8))
    btn_w=72; gap=(bw-4*btn_w-20)//3
    for i,ch in enumerate(choices):
        rx=bx+10+i*(btn_w+gap); ry=by+46
        rect=pygame.Rect(rx,ry,btn_w,68)
        pygame.draw.rect(surface,(70,70,95,230),rect,border_radius=7)
        pygame.draw.rect(surface,(180,160,40,255),rect,1,border_radius=7)
        si=font_lg.render(syms[ch],True,(240,240,240))
        surface.blit(si,(rx+(btn_w-si.get_width())//2,ry+4))
        li=font_sm_global.render(ch[:4].capitalize(),True,(200,200,200))
        surface.blit(li,(rx+(btn_w-li.get_width())//2,ry+46))
        promotion_rects.append((rect,ch))

def handle_promotion_click(pos):
    global promotion_active,promotion_piece,current_turn,_pending_check_update
    for rect,choice in promotion_rects:
        if rect.collidepoint(pos):
            if promotion_piece:
                promotion_piece.name=choice; promotion_piece._load_model()
            promotion_active=False; promotion_piece=None
            current_turn="black" if current_turn=="white" else "white"
            _pending_check_update = True
            return True
    return False


# ==========================
# MAIN LOOP
# ==========================
def main():
    global camera_angle_x,camera_angle_y,camera_distance
    global selected_piece,board_color_theme,pieces
    global promotion_active,current_turn,font_sm_global
    global check_flash_t,game_over,winner,load_menu_active,_pending_check_update

    pygame.init(); pygame.font.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT),DOUBLEBUF|OPENGL)
    pygame.display.set_caption("3D Chess")
    init_opengl(); clock=pygame.time.Clock()

    font_xs = pygame.font.SysFont("segoeuisymbol", SYM_SIZE)
    font_sm = pygame.font.SysFont("segoeui",       16)
    font_md = pygame.font.SysFont("segoeui",       20,bold=True)
    font_lg = pygame.font.SysFont("segoeui",       28,bold=True)
    font_sm_global=font_sm

    overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    dragging=False; drag_start=(0,0); DRAG_THRESH=5
    save_notify=""; save_notify_t=0

    while True:
        clock.tick(60)
        if check_flash_t>0: check_flash_t-=1
        if save_notify_t>0: save_notify_t-=1

        for event in pygame.event.get():
            if event.type==QUIT: pygame.quit(); sys.exit()

            elif event.type==KEYDOWN:
                if event.key==K_ESCAPE:
                    if load_menu_active: load_menu_active=False
                    elif selected_piece: selected_piece.selected=False; selected_piece=None
                elif event.key==K_r:
                    initialize_pieces(); selected_piece=None
                elif event.key==K_n:
                    initialize_pieces(); selected_piece=None
                elif event.key==K_q:
                    global is_checkmate,is_stalemate,in_check
                    game_over=True
                    if winner is None: winner="draw"
                elif event.key==K_s:
                    fname=save_game(slot=1)
                    save_notify=f"Saved: {fname}"; save_notify_t=180
                elif event.key==K_l:
                    load_menu_active=not load_menu_active
                elif event.key==K_m:
                    board_color_theme="dark_blue" if board_color_theme=="black_white" else "black_white"
                elif event.key==K_LEFT:  camera_angle_y-=3
                elif event.key==K_RIGHT: camera_angle_y+=3
                elif event.key==K_UP:    camera_angle_x=max(-10,camera_angle_x-3)
                elif event.key==K_DOWN:  camera_angle_x=min(85,camera_angle_x+3)
                elif event.key==K_z:     camera_distance=max(10,camera_distance-1)
                elif event.key==K_x:     camera_distance=min(60,camera_distance+1)

            elif event.type==MOUSEBUTTONDOWN:
                if   event.button==1: dragging=False; drag_start=event.pos
                elif event.button==4: camera_distance=max(10,camera_distance-1)
                elif event.button==5: camera_distance=min(60,camera_distance+1)

            elif event.type==MOUSEMOTION:
                if pygame.mouse.get_pressed()[0]:
                    dx=event.pos[0]-drag_start[0]; dy=event.pos[1]-drag_start[1]
                    if abs(dx)>DRAG_THRESH or abs(dy)>DRAG_THRESH: dragging=True
                    if dragging:
                        camera_angle_y+=event.rel[0]*0.4
                        camera_angle_x=max(-10,min(85,camera_angle_x+event.rel[1]*0.4))

            elif event.type==MOUSEBUTTONUP:
                if event.button==1 and not dragging:
                    pos=event.pos
                    if load_menu_active:
                        for fname,rect in load_menu_rects.items():
                            if rect.collidepoint(pos):
                                if fname=="__cancel__":
                                    load_menu_active=False
                                else:
                                    if load_game(fname):
                                        load_menu_active=False
                                        save_notify=f"Loaded: {fname}"; save_notify_t=180
                                break
                        continue
                    if game_over:
                        for key,rect in gameover_rects.items():
                            if rect.collidepoint(pos):
                                if key=="new":
                                    initialize_pieces(); selected_piece=None
                                elif key=="saveq":
                                    fname=save_game(); save_notify=f"Saved: {fname}"; save_notify_t=180
                                    game_over=True
                                elif key=="load":
                                    load_menu_active=True
                                elif key=="quit":
                                    pygame.quit(); sys.exit()
                                break
                        continue
                    if promotion_active:
                        handle_promotion_click(pos)
                    else:
                        sq=mouse_to_board(*pos)
                        if sq:
                            tc,tr=sq; clicked=piece_at(tc,tr)
                            if selected_piece is None:
                                if clicked and clicked.color==current_turn:
                                    selected_piece=clicked; clicked.selected=True
                            else:
                                if clicked is selected_piece:
                                    selected_piece.selected=False; selected_piece=None
                                elif clicked and clicked.color==current_turn:
                                    selected_piece.selected=False; selected_piece=clicked; clicked.selected=True
                                else:
                                    if execute_move(selected_piece,tc,tr):
                                        selected_piece.selected=False; selected_piece=None

        for p in pieces: p.animate_step()
        
        if _pending_check_update and not any(p.animating for p in pieces):
            _pending_check_update = False
            _update_check_state()

        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        set_camera(); draw_board(); draw_shadows(); draw_move_highlights()
        checked_king=None
        if in_check and check_flash_t>0: checked_king=_find_king(current_turn,pieces)
        for p in pieces:
            p.draw(flash_red=(p is checked_king and(check_flash_t//8)%2==0))

        draw_overlay(overlay, font_xs, font_sm, font_md, font_lg)
        if promotion_active:
            draw_promotion_menu(overlay, font_md, font_lg)
        if save_notify_t>0:
            ni=font_sm.render(save_notify,True,(100,255,100))
            nx=(WIDTH-ni.get_width())//2; ny=HEIGHT-28
            pygame.draw.rect(overlay,(0,0,0,180),(nx-8,ny-4,ni.get_width()+16,ni.get_height()+8),border_radius=6)
            overlay.blit(ni,(nx,ny))

        overlay_data=pygame.image.tostring(overlay,"RGBA",True)
        glWindowPos2i(0,0)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
        glDrawPixels(WIDTH,HEIGHT,GL_RGBA,GL_UNSIGNED_BYTE,overlay_data)
        glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING); glDisable(GL_BLEND)
        pygame.display.flip()

if __name__=="__main__":
    main()