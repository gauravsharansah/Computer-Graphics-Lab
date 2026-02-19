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
camera_angle_x  = 47.0
camera_angle_y  = 180.0
camera_distance = 28.0
animation_speed = 0.36

# Piece values
PIECE_VALUES = {"pawn":1,"knight":3,"bishop":3,"rook":5,"queen":9,"king":0}

# Turn / state globals
current_turn     = "white"
in_check         = False
is_checkmate     = False
is_stalemate     = False
check_flash_t    = 0
check_flash_color = None   # which color king is flashing ("white"/"black"/None)
game_over        = False
winner           = None
_pending_check_update = False

font_sm_global   = None

# ==========================
# TIME CONTROLS
# ==========================
TIME_OPTIONS = [10*60, 15*60, 30*60]  # seconds
TIME_LABELS  = ["10 min", "15 min", "30 min"]
white_time   = None   # seconds remaining (float), None = untimed
black_time   = None
time_control = 10*60  # default: 10 minutes per player
last_tick_time = None  # pygame.time.get_ticks() at last frame
time_select_active = False  # start game immediately with default timer
time_select_rects  = {}
FLAG_FALLEN = False  # True when a player runs out of time
game_paused = False  # True when game is paused
pause_rect  = None   # clickable pause/resume button rect


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

_auto_save_notify   = ""    # message shown after auto-save
_auto_save_notify_t = 0     # ms remaining to show it
_game_already_saved = False # True when current game state already has a save file

def _auto_save_game():
    global _auto_save_notify, _auto_save_notify_t, _game_already_saved
    if _game_already_saved:
        return   # already has a save file — don't create a duplicate
    fname = _next_save_name()
    save_game(auto_name=fname)
    _game_already_saved = True
    _auto_save_notify   = f"Game auto-saved as {fname}"
    _auto_save_notify_t = 5000  # show for 5 seconds (ms)

def _update_check_state():
    global in_check,is_checkmate,is_stalemate,check_flash_t,game_over,winner
    global check_flash_color, _auto_save_notify, _auto_save_notify_t
    in_check=_king_in_check(current_turn,pieces)
    if in_check:
        check_flash_t=90
        check_flash_color=current_turn
    else:
        check_flash_color=None
    has_moves=has_any_legal_move(current_turn)
    is_checkmate=in_check and not has_moves
    is_stalemate=(not in_check) and (not has_moves)
    if is_checkmate:
        game_over=True; winner="black" if current_turn=="white" else "white"
        _auto_save_game()
    elif is_stalemate:
        game_over=True; winner="draw"
        _auto_save_game()


# ==========================
# SAVE / LOAD
# ==========================
_last_saved_move_count = -1   # track move count at last save to prevent duplicates

def _next_save_name():
    """Return next sequential filename: Game01.json, Game02.json ..."""
    existing = [f for f in os.listdir(SAVES_DIR) if f.startswith("Game") and f.endswith(".json")]
    nums = []
    for f in existing:
        try: nums.append(int(f[4:6]))
        except: pass
    n = max(nums)+1 if nums else 1
    return f"Game{n:02d}.json"

def save_game(auto_name=None):
    global _last_saved_move_count
    # Never save in the starting position (no moves played yet)
    if len(move_history) == 0:
        return None
    # Prevent duplicate saves (same position saved twice without any new move)
    if auto_name is None:   # manual save — enforce no-duplicate rule
        if len(move_history) == _last_saved_move_count:
            return None   # nothing new to save
    fname = auto_name if auto_name else _next_save_name()
    path=os.path.join(SAVES_DIR,fname)
    data={
        "current_turn":current_turn,
        "pieces":[p.to_dict() for p in pieces],
        "captured_by_white":captured_by_white,
        "captured_by_black":captured_by_black,
        "move_history":move_history,
        "last_pawn_double": None if last_pawn_double is None else last_pawn_double.to_dict(),
        "white_time": white_time,
        "black_time": black_time,
        "time_control": time_control,
    }
    with open(path,"w") as f: json.dump(data,f,indent=2)
    _last_saved_move_count = len(move_history)
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
    global white_time, black_time, last_tick_time, FLAG_FALLEN, time_select_active
    global time_control
    saved_tc = data.get("time_control", time_control)
    time_control = saved_tc
    wt = data.get("white_time")
    bt = data.get("black_time")
    # If save has time data, restore it; otherwise fall back to full time_control
    if wt is not None and bt is not None:
        white_time = float(wt)
        black_time = float(bt)
    elif time_control is not None:
        white_time = float(time_control)
        black_time = float(time_control)
    else:
        white_time = None
        black_time = None
    last_tick_time=None; FLAG_FALLEN=False; time_select_active=False
    global game_paused; game_paused=False
    global _game_already_saved; _game_already_saved = True   # loaded = already on disk
    _update_check_state()
    return True

def list_saves():
    saves=sorted([f for f in os.listdir(SAVES_DIR) if f.endswith(".json")], reverse=True)
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
    global white_time,black_time,last_tick_time,FLAG_FALLEN,time_select_active
    if time_control is not None:
        white_time=float(time_control); black_time=float(time_control)
    else:
        white_time=None; black_time=None
    last_tick_time=None; FLAG_FALLEN=False; time_select_active=False
    global game_paused; game_paused=False
    global _game_already_saved; _game_already_saved = False
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
    glClearColor(0.34, 0.52, 0.20, 1.0)   # garden grass green
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(45,WIDTH/HEIGHT,0.1,200)
    glMatrixMode(GL_MODELVIEW)


def set_camera():
    glLoadIdentity()
    glTranslatef(BOARD_OFFSET_X, BOARD_OFFSET_Y,-camera_distance)
    glRotatef(camera_angle_x,1,0,0)
    glRotatef(camera_angle_y,0,1,0)


def draw_background():
    """Paint a garden-style gradient background: sky at top, grass at bottom."""
    glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    glOrtho(0,1,0,1,-1,1)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glBegin(GL_QUADS)
    # Top-left  – sky blue
    glColor3f(0.40, 0.68, 0.90); glVertex2f(0,1)
    # Top-right – sky blue
    glColor3f(0.50, 0.78, 0.98); glVertex2f(1,1)
    # Bottom-right – warm grass green
    glColor3f(0.22, 0.48, 0.14); glVertex2f(1,0)
    # Bottom-left – warm grass green
    glColor3f(0.18, 0.42, 0.10); glVertex2f(0,0)
    glEnd()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()
    glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING)


# ==========================
# DRAW BOARD
# ==========================
def draw_board():
    glDisable(GL_LIGHTING)
    for col in range(BOARD_SIZE):
        for row in range(BOARD_SIZE):
            if board_color_theme=="red_white":
                light,dark=(0.75,0.85,0.95),(0.75,0.25,0.30)
            else:
                light,dark=(0.94,0.88,0.70),(0.05,0.10,0.45)
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
    glColor3f(0.65,0.65,0.65); glBegin(GL_QUADS)
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
                     player_label, label_col, piece_col, bg_col, border_col, badge_col, adv_for_this_player):
        pygame.draw.rect(surface, bg_col, (PANEL_X, strip_y, STRIP_W, strip_h), border_radius=6)
        pygame.draw.rect(surface, border_col, (PANEL_X, strip_y, STRIP_W, strip_h), 1, border_radius=6)
        pl_img = font_sm.render(player_label, True, label_col)
        surface.blit(pl_img,(PANEL_X+8, strip_y+4))
        cx=PANEL_X+8; cy=strip_y+24
        counts = count(captured_list)
        for pname in ORDER:
            cnt = counts.get(pname,0)
            if cnt==0: continue
            for _ in range(cnt):
                pi = font_xs.render(SYMS.get(pname,"?"), True, piece_col)
                surface.blit(pi,(cx,cy)); cx+=pi.get_width()+SYM_PAD
                if cx > PANEL_X+STRIP_W-18:
                    cx=PANEL_X+8; cy+=pi.get_height()+2
        if adv_for_this_player and adv_amt>0:
            badge = font_sm.render(f"+{adv_amt}", True, badge_col)
            bx=cx+6; by=cy+2
            if bx+badge.get_width()+6 > PANEL_X+STRIP_W:
                bx=PANEL_X+8; by=cy+font_xs.get_height()+4
            surface.blit(badge,(bx,by))

    top_y=B_CAP_Y; strip_h=STRIP_H
    # Top panel: "Black captured" = white pieces captured by black player
    # Show pieces in WHITE color on DARK background (white pieces on dark bg)
    render_strip(surface, captured_by_black, top_y, strip_h,
                 "Black", (200,200,200),
                 piece_col=(240,240,240),        # white piece symbols
                 bg_col=(25,25,35,210),           # dark background
                 border_col=(80,70,40,160),
                 badge_col=(240,240,240),         # white +N badge on dark bg
                 adv_for_this_player=(adv_color=="black"))

    bot_y = W_CAP_Y
    # Bottom panel: "White captured" = black pieces captured by white player
    # Show pieces in BLACK color on LIGHT background (black pieces on light bg)
    render_strip(surface, captured_by_white, bot_y, strip_h,
                 "White", (30,30,30),
                 piece_col=(15,10,5),             # dark/black piece symbols
                 bg_col=(210,200,175,220),         # light/cream background
                 border_col=(140,120,60,200),
                 badge_col=(20,15,5),              # dark +N badge on light bg
                 adv_for_this_player=(adv_color=="white"))


# ==========================
# TIME SELECTION SCREEN
# ==========================
def draw_time_select(surface, font_sm, font_md, font_lg):
    global time_select_rects
    time_select_rects = {}
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0,0,0,200)); surface.blit(ov,(0,0))
    bw,bh = 460,300; bx=(WIDTH-bw)//2; by=(HEIGHT-bh)//2
    pygame.draw.rect(surface,(18,20,35,250),(bx,by,bw,bh),border_radius=14)
    pygame.draw.rect(surface,(200,180,50,255),(bx,by,bw,bh),2,border_radius=14)
    pygame.draw.rect(surface,(40,35,10,230),(bx+2,by+2,bw-4,56),border_radius=12)
    ti = font_lg.render("Select Time Control", True, (230,210,80))
    surface.blit(ti,(bx+(bw-ti.get_width())//2, by+14))
    sub = font_sm.render("Choose a time limit per player for the whole game", True, (180,170,140))
    surface.blit(sub,(bx+(bw-sub.get_width())//2, by+58))
    BTN_W,BTN_H = 110,80; gap=20
    total_w = len(TIME_OPTIONS)*(BTN_W+gap)-gap
    sx = bx+(bw-total_w)//2; sy=by+92
    for i,(secs,label) in enumerate(zip(TIME_OPTIONS,TIME_LABELS)):
        rx=sx+i*(BTN_W+gap)
        r=pygame.Rect(rx,sy,BTN_W,BTN_H)
        pygame.draw.rect(surface,(40,80,140,230),r,border_radius=10)
        pygame.draw.rect(surface,(160,140,40,255),r,2,border_radius=10)
        mins=secs//60
        big=font_lg.render(f"{mins}", True,(240,240,240))
        surface.blit(big,(rx+(BTN_W-big.get_width())//2, sy+10))
        sm=font_sm.render("min", True,(180,190,210))
        surface.blit(sm,(rx+(BTN_W-sm.get_width())//2, sy+50))
        time_select_rects[secs]=r
    # No timer button
    nr=pygame.Rect(bx+(bw-150)//2, sy+BTN_H+20, 150, 44)
    pygame.draw.rect(surface,(60,55,50,200),nr,border_radius=8)
    pygame.draw.rect(surface,(120,110,60,200),nr,1,border_radius=8)
    nl=font_md.render("No Timer", True,(200,200,190))
    surface.blit(nl,(nr.x+(150-nl.get_width())//2, nr.y+(44-nl.get_height())//2))
    time_select_rects[0]=nr

def handle_time_select_click(pos):
    global time_control, time_select_active, white_time, black_time
    global last_tick_time, FLAG_FALLEN
    for secs,rect in time_select_rects.items():
        if rect.collidepoint(pos):
            time_control = secs if secs>0 else None
            time_select_active = False
            if time_control:
                white_time=float(time_control); black_time=float(time_control)
            else:
                white_time=None; black_time=None
            last_tick_time=None; FLAG_FALLEN=False
            return True
    return False


# ==========================
# DRAW CLOCK DISPLAY
# ==========================
# Layout constants shared between draw_clocks and draw_chesscom_captured
CLOCK_H   = 44
STRIP_H   = 68
LABEL_GAP = 22
CLOCK_GAP = 6
CX_CLOCK  = WIDTH - 185
CW_CLOCK  = 175

# Black block (top of right panel):
#   label at y=22, clock at y=44, captured at y=94
B_CLOCK_Y = 44
B_CAP_Y   = B_CLOCK_Y + CLOCK_H + CLOCK_GAP   # 94

# White block (bottom of right panel):
#   captured near bottom, clock above it, label above clock
W_CAP_Y   = HEIGHT - STRIP_H - 30              # 552
W_CLOCK_Y = W_CAP_Y - CLOCK_H - CLOCK_GAP     # 502
W_LABEL_Y = W_CLOCK_Y - LABEL_GAP             # 480

def draw_clocks(surface, font_md, font_lg):
    global pause_rect
    if white_time is None and black_time is None: return
    def fmt(t):
        t=max(0,int(t)); m=t//60; s=t%60
        return f"{m}:{s:02d}"
    wt=white_time if white_time is not None else 0
    bt=black_time  if black_time  is not None else 0
    w_active=(current_turn=="white") and not game_over and not game_paused
    b_active=(current_turn=="black") and not game_over and not game_paused
    w_low = wt<30
    b_low = bt<30
    def draw_clock_box(y, remaining, active, low):
        bg=(60,120,60,230) if active else (30,30,40,200)
        border=(80,200,80,255) if active else (80,70,40,160)
        if low:
            bg=(140,30,30,230) if active else (80,20,20,200)
            border=(255,80,80,255) if active else (160,50,50,160)
        if game_paused:
            bg=(50,50,80,220); border=(160,140,60,200)
        pygame.draw.rect(surface,bg,(CX_CLOCK,y,CW_CLOCK,CLOCK_H),border_radius=8)
        pygame.draw.rect(surface,border,(CX_CLOCK,y,CW_CLOCK,CLOCK_H),2,border_radius=8)
        tc=(255,255,255) if active else (160,160,160)
        if low and not game_paused: tc=(255,180,180) if active else (200,100,100)
        if game_paused: tc=(180,175,210)
        txt=font_lg.render(fmt(remaining),True,tc)
        surface.blit(txt,(CX_CLOCK+(CW_CLOCK-txt.get_width())//2, y+(CLOCK_H-txt.get_height())//2))

    # Draw black clock and label
    draw_clock_box(B_CLOCK_Y, bt, b_active, b_low)
    # "Black" label — sky-blue tint to suit garden background
    blab=font_md.render("Black",True,(30,60,140))
    surface.blit(blab,(CX_CLOCK+(CW_CLOCK-blab.get_width())//2, B_CLOCK_Y-LABEL_GAP+2))

    # Draw white clock and label
    draw_clock_box(W_CLOCK_Y, wt, w_active, w_low)
    # "White" label — dark grass-green tint to suit garden background
    wlab=font_md.render("White",True,(20,80,20))
    surface.blit(wlab,(CX_CLOCK+(CW_CLOCK-wlab.get_width())//2, W_LABEL_Y+2))

    # ── Pause / Resume button — centred between black block bottom and white block top ──
    if not game_over and not time_select_active:
        black_block_bottom = B_CAP_Y + STRIP_H          # 162
        white_block_top    = W_LABEL_Y                   # 480
        mid_y = (black_block_bottom + white_block_top) // 2
        btn_w, btn_h = 120, 32
        btn_x = CX_CLOCK + (CW_CLOCK - btn_w) // 2
        btn_y = mid_y - btn_h // 2
        if game_paused:
            bg=(70,130,70,240); border=(100,210,100,255); label="▶  Resume"
        else:
            bg=(60,60,100,220); border=(120,110,160,255); label="⏸  Pause"
        r = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(surface, bg, r, border_radius=7)
        pygame.draw.rect(surface, border, r, 2, border_radius=7)
        lbl = font_md.render(label, True, (230,230,230))
        surface.blit(lbl, (btn_x+(btn_w-lbl.get_width())//2, btn_y+(btn_h-lbl.get_height())//2))
        pause_rect = r

    # ── Pause overlay on board area ────────────────────────────────────────
    if game_paused:
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 0))
        board_area = pygame.Rect(0, 0, WIDTH - 190, HEIGHT)
        pygame.draw.rect(ov, (0, 0, 0, 160), board_area)
        surface.blit(ov, (0, 0))
        bx = (WIDTH - 190) // 2
        pi_font = pygame.font.SysFont("segoeui", 48, bold=True)
        pi = pi_font.render("PAUSED", True, (230, 210, 80))
        px = bx - pi.get_width() // 2
        py = HEIGHT // 2 - pi.get_height() // 2
        pygame.draw.rect(surface, (20, 18, 10, 220),
                         (px-20, py-14, pi.get_width()+40, pi.get_height()+28), border_radius=12)
        pygame.draw.rect(surface, (200, 180, 50, 200),
                         (px-20, py-14, pi.get_width()+40, pi.get_height()+28), 2, border_radius=12)
        surface.blit(pi, (px, py))
        hint = font_md.render("Press P or click Resume to continue", True, (180, 170, 130))
        surface.blit(hint, (bx - hint.get_width()//2, py + pi.get_height() + 18))


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
    elif winner=="quit":
        title_txt="Game Quit"; title_col=(200,200,200)
        bar_col=(50,50,50,230)
    elif winner=="white":
        title_txt="WHITE  WINS!"; title_col=(255,255,220)
        bar_col=(40,40,40,240)
    else:
        title_txt="BLACK  WINS!"; title_col=(255,220,30)
        bar_col=(40,30,5,240)
    
    pygame.draw.rect(surface,bar_col,(bx+2,by+2,bw-4,72),border_radius=12)
    font_xl=pygame.font.SysFont("segoeui",34,bold=True)
    ti=font_xl.render(title_txt,True,title_col)
    surface.blit(ti,(bx+(bw-ti.get_width())//2, by+20))
    
    sub_txt=""
    if FLAG_FALLEN:
        sub_txt="on time (flag fallen)"
    elif winner=="quit":
        sub_txt="Game was quit by player"
    elif winner=="draw":
        sub_txt="by Stalemate"
    elif winner and winner!="draw":
        sub_txt="by Checkmate"
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

    # ── Move history — grows 5→15 pairs, then scrolls top-down ──────────────
    MIN_ROWS = 5
    MAX_ROWS = 15
    ROW_H    = 20
    hist_w   = 170

    white_moves = [m for m in move_history if m["color"]=="white"]
    black_moves = [m for m in move_history if m["color"]=="black"]

    # Build pairs: (white_label, black_label_or_None)
    total_pairs = len(white_moves)
    pairs = []
    for i in range(total_pairs):
        w = white_moves[i]["label"]
        b = black_moves[i]["label"] if i < len(black_moves) else None
        pairs.append((w, b))

    # How many rows to display (clamped between MIN and MAX)
    display_rows = max(MIN_ROWS, min(total_pairs, MAX_ROWS))

    # Which pairs to show: always the latest display_rows pairs
    visible = pairs[-display_rows:] if len(pairs) > display_rows else pairs

    # Panel height based on display_rows (fixed once at MAX)
    hist_h = display_rows * ROW_H + 56

    pygame.draw.rect(surface,(0,0,0,170),(5,5,hist_w,hist_h),border_radius=8)
    pygame.draw.rect(surface,(200,180,50,130),(5,5,hist_w,hist_h),1,border_radius=8)
    lbl=font_md.render("Move History",True,(220,200,80))
    surface.blit(lbl,(12,10))
    pygame.draw.line(surface,(180,160,50),(12,32),(hist_w-8,32),1)

    wh=font_sm.render("White",True,(230,230,230))
    bh_lbl=font_sm.render("Black",True,(160,160,255))
    surface.blit(wh,(22,36))
    surface.blit(bh_lbl,(110,36))

    y_start = 56
    for i, (w_lbl, b_lbl) in enumerate(visible):
        y = y_start + i * ROW_H
        surface.blit(font_sm.render(w_lbl, True, (230,230,230)), (22, y))
        if b_lbl:
            surface.blit(font_sm.render(b_lbl, True, (160,160,255)), (110, y))

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

    # ── Controls panel — 3 columns ─────────────────────────────────────────
    col_mouse=[
        ("── Mouse ──",True),
        ("Left-click piece","Select piece"),
        ("Left-click sq.","Move / capture"),
        ("Left-drag","Orbit camera"),
        ("Scroll wheel","Zoom in/out"),
    ]
    col_keys1=[
        ("── Keys A ──",True),
        ("Arrow ← →","Rotate L/R"),
        ("Arrow ↑ ↓","Tilt up/down"),
        ("Z / X","Zoom in/out"),
        ("M","Board theme"),
        ("S","Save game"),
    ]
    col_keys2=[
        ("── Keys B ──",True),
        ("L","Load menu"),
        ("N","New game"),
        ("P","Pause/Resume"),
        ("Q","Quit game"),
        ("R","Hard reset"),
        ("Esc","Deselect"),
    ]
    rh=16; pad=6; cw=223
    rows=max(len(col_mouse),len(col_keys1),len(col_keys2))
    ph=rows*rh+pad*2+4
    pw=cw*3+pad*2+8
    py=HEIGHT-ph-5
    pygame.draw.rect(surface,(0,0,0,170),(5,py,pw,ph),border_radius=8)
    pygame.draw.rect(surface,(200,180,50,100),(5,py,pw,ph),1,border_radius=8)
    for ci_,col_lines in enumerate((col_mouse,col_keys1,col_keys2)):
        px2=12+ci_*(cw+4); cy2=py+pad
        for item in col_lines:
            hd=(item[1] is True)
            kt=item[0]; dt="" if hd else item[1]
            kc=(220,200,80) if hd else (180,220,255)
            surface.blit(font_sm.render(kt,True,kc),(px2,cy2))
            if not hd and dt:
                surface.blit(font_sm.render(dt,True,(200,200,200)),(px2+108,cy2))
            cy2+=rh

    # ── Captured pieces panel ──────────────────────────────────────────────
    draw_chesscom_captured(surface, font_xs, font_sm, font_md)
    # ── Clocks ─────────────────────────────────────────────────────────────
    draw_clocks(surface, font_md, font_lg)

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
            # is_light = (col) % 2 == 0
            # txt_col = (40,30,15) if is_light else (220,200,150)

            txt_col = (0,255,0)
            lbl = coord_font.render(files[col], True, txt_col)
            surface.blit(lbl, (int(sx - lbl.get_width()//2), int(sy - lbl.get_height()//2)))
        except: pass
    
    for row in range(8):
        wx = BOARD_HALF + 0.3
        wz = (row - BOARD_SIZE/2.0 + 0.5)*SQUARE_SIZE
        try:
            sx, sy, _ = gluProject(wx, 0.0, wz, modelview, projection, viewport)
            sy = viewport[3] - sy

            txt_col = (0,255,0)
            lbl = coord_font.render(ranks[row], True, txt_col)
            surface.blit(lbl, (int(sx - lbl.get_width()//2), int(sy - lbl.get_height()//2)))
        except: pass

    # ── Game over / load menus ─────────────────────────────────────────────
    if time_select_active:
        draw_time_select(surface, font_sm, font_md, font_lg)
    elif game_over:
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
    # Use color-appropriate symbols based on whose pawn is promoting
    if promotion_piece and promotion_piece.color == "white":
        syms={"queen":"♕","rook":"♖","bishop":"♗","knight":"♘"}
    else:
        syms={"queen":"♛","rook":"♜","bishop":"♝","knight":"♞"}
    bw,bh=380,130; bx=(WIDTH-bw)//2; by=(HEIGHT-bh)//2
    pygame.draw.rect(surface,(25,25,40,230),(bx,by,bw,bh),border_radius=10)
    pygame.draw.rect(surface,(200,180,50,255),(bx,by,bw,bh),2,border_radius=10)
    t=font_md.render("Promote pawn to:",True,(220,200,80))
    surface.blit(t,(bx+(bw-t.get_width())//2,by+8))
    btn_w=76; gap=(bw-4*btn_w-20)//3
    sym_font = pygame.font.SysFont("segoeuisymbol", 38, bold=True)
    for i,ch in enumerate(choices):
        rx=bx+10+i*(btn_w+gap); ry=by+38
        rect=pygame.Rect(rx,ry,btn_w,76)
        pygame.draw.rect(surface,(70,70,95,230),rect,border_radius=7)
        pygame.draw.rect(surface,(180,160,40,255),rect,1,border_radius=7)
        # Draw large symbol centred in button
        si=sym_font.render(syms[ch],True,(240,240,240))
        surface.blit(si,(rx+(btn_w-si.get_width())//2, ry+(76-si.get_height())//2))
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
    global is_checkmate,is_stalemate,in_check,check_flash_color
    global white_time,black_time,last_tick_time,FLAG_FALLEN,time_select_active,time_control
    global game_paused, pause_rect
    global _last_saved_move_count, _auto_save_notify, _auto_save_notify_t, _game_already_saved

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
    dragging=False; drag_start=(0,0); DRAG_THRESH=5; _drag_allowed=True
    save_notify=""; save_notify_t=0   # ms remaining

    while True:
        clock.tick(60)
        dt_ms = clock.get_time()
        if check_flash_t>0: check_flash_t-=1
        if save_notify_t>0:        save_notify_t        = max(0, save_notify_t - dt_ms)
        if _auto_save_notify_t>0:  _auto_save_notify_t  = max(0, _auto_save_notify_t - dt_ms)

        # ── Tick clocks ────────────────────────────────────────────────────
        _any_animating = any(p.animating for p in pieces)
        if not time_select_active and not game_over and not promotion_active and not game_paused and not _any_animating:
            if white_time is not None or black_time is not None:
                dt_sec = dt_ms / 1000.0
                if current_turn=="white" and white_time is not None:
                    white_time = max(0.0, white_time - dt_sec)
                    if white_time<=0 and not FLAG_FALLEN:
                        FLAG_FALLEN=True; game_over=True; winner="black"; _auto_save_game()
                elif current_turn=="black" and black_time is not None:
                    black_time = max(0.0, black_time - dt_sec)
                    if black_time<=0 and not FLAG_FALLEN:
                        FLAG_FALLEN=True; game_over=True; winner="white"; _auto_save_game()

        for event in pygame.event.get():
            if event.type==QUIT: pygame.quit(); sys.exit()

            elif event.type==KEYDOWN:
                if event.key==K_ESCAPE:
                    if load_menu_active: load_menu_active=False
                    elif game_paused: game_paused=False
                    elif selected_piece:
                        selected_piece.selected=False; selected_piece=None; _drag_allowed=True
                elif event.key==K_p:
                    if not game_over and not time_select_active:
                        game_paused = not game_paused
                elif event.key==K_r:
                    # Hard reset: delete ALL saved games then start fresh
                    for f in os.listdir(SAVES_DIR):
                        if f.endswith(".json"):
                            try: os.remove(os.path.join(SAVES_DIR,f))
                            except: pass
                    time_select_active=True; selected_piece=None; _drag_allowed=True
                elif event.key==K_n:
                    time_select_active=True; selected_piece=None
                elif event.key==K_q:
                    if not game_over:
                        game_over=True; winner="quit"
                elif event.key==K_s:
                    fname=save_game()
                    if fname:
                        save_notify=f"Saved: {fname}"; save_notify_t=5000
                    elif len(move_history)==0:
                        save_notify="No moves played yet — nothing to save"; save_notify_t=5000
                    else:
                        save_notify="Already saved (play a move first)"; save_notify_t=5000
                elif event.key==K_l:
                    load_menu_active=not load_menu_active
                elif event.key==K_m:
                    board_color_theme="red_white" if board_color_theme=="blue_white" else "blue_white"
                elif event.key==K_LEFT:  camera_angle_y-=3
                elif event.key==K_RIGHT: camera_angle_y+=3
                elif event.key==K_UP:    camera_angle_x=max(-10,camera_angle_x-3)
                elif event.key==K_DOWN:  camera_angle_x=min(85,camera_angle_x+3)
                elif event.key==K_z:     camera_distance=max(10,camera_distance-1)
                elif event.key==K_x:     camera_distance=min(60,camera_distance+1)

            elif event.type==MOUSEBUTTONDOWN:
                if event.button==1:
                    dragging=False; drag_start=event.pos
                    # Only allow drag-to-orbit when no piece is selected and not animating
                    _drag_allowed = (selected_piece is None) and not _any_animating
                elif event.button==4: camera_distance=max(10,camera_distance-1)
                elif event.button==5: camera_distance=min(60,camera_distance+1)

            elif event.type==MOUSEMOTION:
                if pygame.mouse.get_pressed()[0] and _drag_allowed and selected_piece is None:
                    dx=event.pos[0]-drag_start[0]; dy=event.pos[1]-drag_start[1]
                    if abs(dx)>DRAG_THRESH or abs(dy)>DRAG_THRESH: dragging=True
                    if dragging:
                        camera_angle_y+=event.rel[0]*0.4
                        camera_angle_x=max(-10,min(85,camera_angle_x+event.rel[1]*0.4))

            elif event.type==MOUSEBUTTONUP:
                if event.button==1:
                    was_dragging = dragging
                    dragging = False   # always reset on button-up
                    if was_dragging: continue   # skip click logic if it was a drag
                    pos=event.pos
                    if time_select_active:
                        handle_time_select_click(pos)
                        if not time_select_active:
                            initialize_pieces()
                        continue
                    # ── Pause button (always clickable unless game over / time select) ──
                    if not game_over and pause_rect and pause_rect.collidepoint(pos):
                        game_paused = not game_paused
                        continue
                    if game_paused: continue   # block all other clicks while paused
                    if load_menu_active:
                        for fname,rect in load_menu_rects.items():
                            if rect.collidepoint(pos):
                                if fname=="__cancel__":
                                    load_menu_active=False
                                else:
                                    if load_game(fname):
                                        load_menu_active=False
                                        save_notify=f"Loaded: {fname}"; save_notify_t=5000
                                break
                        continue
                    if game_over:
                        for key,rect in gameover_rects.items():
                            if rect.collidepoint(pos):
                                if key=="new":
                                    time_select_active=True; selected_piece=None
                                elif key=="saveq":
                                    _an=_next_save_name(); fname=save_game(auto_name=_an)
                                    save_notify=f"Saved: {fname}"; save_notify_t=5000
                                    game_over=True
                                elif key=="load":
                                    load_menu_active=True
                                elif key=="quit":
                                    pygame.quit(); sys.exit()
                                break
                        continue
                    if promotion_active:
                        handle_promotion_click(pos)
                    elif game_paused:
                        # Only allow clicking the pause/resume button
                        if pause_rect and pause_rect.collidepoint(pos):
                            game_paused = False
                    elif _any_animating:
                        pass  # silently block all board clicks during animation
                    else:
                        sq=mouse_to_board(*pos)
                        if sq:
                            tc,tr=sq; clicked=piece_at(tc,tr)
                            if selected_piece is None:
                                if clicked and clicked.color==current_turn:
                                    selected_piece=clicked; clicked.selected=True
                                    _drag_allowed=False  # lock camera while piece selected
                            else:
                                if clicked is selected_piece:
                                    selected_piece.selected=False; selected_piece=None
                                    _drag_allowed=True
                                elif clicked and clicked.color==current_turn:
                                    selected_piece.selected=False; selected_piece=clicked; clicked.selected=True
                                else:
                                    if execute_move(selected_piece,tc,tr):
                                        selected_piece.selected=False; selected_piece=None
                                        _drag_allowed=True

        for p in pieces: p.animate_step()
        
        if _pending_check_update and not any(p.animating for p in pieces):
            _pending_check_update = False
            _update_check_state()

        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        draw_background()
        set_camera(); draw_board(); draw_shadows(); draw_move_highlights()
        checked_king=None
        if in_check and check_flash_t>0 and check_flash_color:
            checked_king=_find_king(check_flash_color,pieces)
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
        if _auto_save_notify_t>0:
            ani=font_sm.render(_auto_save_notify,True,(255,220,80))
            anx=(WIDTH-ani.get_width())//2; any_=HEIGHT-52
            pygame.draw.rect(overlay,(0,0,0,180),(anx-8,any_-4,ani.get_width()+16,ani.get_height()+8),border_radius=6)
            overlay.blit(ani,(anx,any_))

        overlay_data=pygame.image.tostring(overlay,"RGBA",True)
        glWindowPos2i(0,0)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
        glDrawPixels(WIDTH,HEIGHT,GL_RGBA,GL_UNSIGNED_BYTE,overlay_data)
        glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING); glDisable(GL_BLEND)
        pygame.display.flip()

if __name__=="__main__":
    main()