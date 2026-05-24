import pygame, sys, math, random, os
pygame.init()

pygame.init()
pygame.mixer.init()   

# Safe sound loading (won't crash if files missing)
try:
    eat_sound = pygame.mixer.Sound("eat.wav")
except:
    print("Warning: eat.wav not found - creating silent sound")
    eat_sound = pygame.mixer.Sound(buffer=bytes([0]) * 1000)

try:
    gameover_sound = pygame.mixer.Sound("gameover.wav")
except:
    print("Warning: gameover.wav not found - creating silent sound")
    gameover_sound = pygame.mixer.Sound(buffer=bytes([0]) * 1000)

try:
    pygame.mixer.music.load("music.mp3")
    pygame.mixer.music.play(-1)
except:
    print("Warning: music.mp3 not found - playing without music")

# Window setup
W, H = 1000, 580
GY = H - 110
PS = 40
MAX_PS = 120
MIN_PS = 40
SIZE_PER_COIN = 3
FPS = 60
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Geometry Dash")
clock = pygame.time.Clock()

# Physics
GRAV = 0.62
J1 = -13.8
J2 = -12.2
SPD0 = 6.0
SPMAX = 13.0
SINC = 0.0007

# Colors
SKY1 = (10,20,40)
SKY2 = (30,50,90)
GND = (60,40,30)
GNDL = (90,60,45)
PC = (0,255,180)
PC2 = (0,200,140)
SC = (255,30,30)
BC = (255,100,20)
BC2 = (200,70,10)
FC = (180,80,255)
FC2 = (140,40,200)
CC = (255,215,0)
W2 = (255,255,255)
DK = (40,30,20)
HC = (255,95,50)

# Fonts
FB = pygame.font.SysFont("impact", 60, bold=True)
FM = pygame.font.SysFont("impact", 32)
FS = pygame.font.SysFont("trebuchetms", 16, bold=True)
TITLE_FONT = pygame.font.Font(None, 80)

# Animation variables
pulse_value = 0
rainbow_offset = 0
menu_particles = []
screen_shake = 0
glitch_offset = 0

# Helper functions
def lerp(a,b,t):
    return a+(b-a)*t

def clamp(v,lo,hi):
    return max(lo,min(hi,v))

def txt(s, f, t, c, cx, y):
    surf = f.render(t, True, c)
    s.blit(surf, (cx - surf.get_width()//2, y))

def glow_rect(s, col, r, rad=8, a=65):
    if r[2] <= 0 or r[3] <= 0:
        return
    g = pygame.Surface((r[2]+rad*4, r[3]+rad*4), pygame.SRCALPHA)
    for i in range(rad, 0, -2):
        pygame.draw.rect(g, (*col, int(a*i/rad)), (rad*2-i, rad*2-i, r[2]+i*2, r[3]+i*2), border_radius=4)
    s.blit(g, (r[0]-rad*2, r[1]-rad*2))

def glow_circle(s, col, pos, r, a=90):
    g = pygame.Surface((r*6, r*6), pygame.SRCALPHA)
    for i in range(r*2, 0, -3):
        pygame.draw.circle(g, (*col, int(a*i/(r*2))), (r*3, r*3), i)
    s.blit(g, (pos[0]-r*3, pos[1]-r*3))

def rainbow_color(offset):
    colors = [(255,0,0), (255,127,0), (255,255,0), (0,255,0), (0,0,255), (75,0,130), (148,0,211)]
    idx = int(offset) % len(colors)
    return colors[idx]

# Particles
parts = []

def emit(x, y, col, n=6, vx=None, vy=None, life=None, sz=None):
    for _ in range(n):
        l = life or random.uniform(0.3, 0.8)
        parts.append([
            float(x), float(y),
            vx if vx is not None else random.uniform(-4, 4),
            vy if vy is not None else random.uniform(-6, -1),
            l, l,
            sz or random.uniform(3, 7), col
        ])

def explode(x, y, cols):
    for c in cols:
        for _ in range(7):
            l = random.uniform(0.5, 1.3)
            parts.append([float(x), float(y), random.uniform(-8,8), random.uniform(-9,1), l, l, random.uniform(4,11), c])

def upd_parts(s, dt):
    alive_p = []
    for p in parts:
        p[0] += p[2]
        p[1] += p[3]
        p[3] += 0.16
        p[4] -= dt
        if p[4] > 0:
            a = int(255 * p[4] / p[5])
            sz = max(1, int(p[6] * p[4] / p[5]))
            surf = pygame.Surface((sz*2, sz*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p[7][:3], a), (sz, sz), sz)
            s.blit(surf, (int(p[0])-sz, int(p[1])-sz))
            alive_p.append(p)
    parts[:] = alive_p

# Trail
trail = []

def draw_trail(s):
    for i, (x, y) in enumerate(trail):
        ratio = i / max(1, len(trail))
        r = max(1, int(ratio * 9))
        a = int(ratio * 150)
        surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*PC, a), (r, r), r)
        s.blit(surf, (x-r, y-r))

# Player state
px_ = py_ = pvy = prot = pspd = 0.0
on_gnd = alive = True
jump_n = 0
sq_y = 1.0
sq_vy = 0.0
combo = 0
combo_t = 0.0
current_player_size = PS

def reset_player():
    global px_, py_, pvy, prot, pspd, on_gnd, alive, jump_n, sq_y, sq_vy, combo, combo_t, current_player_size
    px_, py_, pvy, prot, pspd = 160.0, float(GY-PS), 0.0, 0.0, 0.0
    on_gnd = True
    alive = True
    jump_n = 0
    sq_y = 1.0
    sq_vy = 0.0
    combo = 0
    combo_t = 0.0
    current_player_size = PS
    trail.clear()

def upd_player(dt, platform_rects):
    global py_, pvy, on_gnd, prot, pspd, jump_n, sq_y, sq_vy, combo_t, current_player_size
    pvy += GRAV
    py_ += pvy

    was_grnd = on_gnd
    on_gnd = False

    if py_ + current_player_size >= GY:
        py_ = GY - current_player_size
        pvy = 0
        if not was_grnd:
            sq_vy = -0.28
        on_gnd = True
        jump_n = 0

    for pr2 in platform_rects:
        feet = pygame.Rect(px_+4, int(py_+current_player_size)-4, current_player_size-8, 8)
        if feet.colliderect(pr2) and pvy >= 0:
            py_ = float(pr2.top - current_player_size)
            pvy = 0
            if not was_grnd:
                sq_vy = -0.28
            on_gnd = True
            jump_n = 0

    if not on_gnd:
        prot += pspd
    else:
        prot = lerp(prot, round(prot/90)*90, 0.2)
        pspd = lerp(pspd, 0, 0.15)

    sq_vy += (1 - sq_y) * 0.25
    sq_vy *= 0.7
    sq_y = clamp(sq_y + sq_vy, 0.6, 1.4)

    trail.append((int(px_ + current_player_size//2), int(py_ + current_player_size//2)))
    if len(trail) > 18:
        trail.pop(0)

    combo_t = max(0, combo_t - dt)
    if on_gnd and random.random() < 0.3:
        emit(px_, py_+current_player_size, GND, n=1, vx=random.uniform(-2,-1), vy=random.uniform(-2,0), life=0.12, sz=3)

def do_jump():
    global pvy, on_gnd, jump_n, pspd, sq_vy, current_player_size
    if jump_n < 2:
        vel = J1 if jump_n == 0 else J2
        pvy = vel
        on_gnd = False
        jump_n += 1
        pspd = 9.0
        sq_vy = 0.45
        col = PC if jump_n == 1 else (255,200,80)
        emit(int(px_+current_player_size//2), int(py_+current_player_size//2), col, n=6, life=0.28, sz=5)
        if jump_n == 2:
            for ang in range(0, 360, 45):
                r = math.radians(ang)
                emit(int(px_+current_player_size//2), int(py_+current_player_size//2), (255,200,80), n=1,
                     vx=math.cos(r)*5, vy=math.sin(r)*5, life=0.35, sz=4)
        return True
    return False

def draw_player(s):
    cx = px_ + current_player_size//2
    cy = py_ + current_player_size//2
    draw_trail(s)
    glow_rect(s, PC, (int(px_), int(py_), current_player_size, current_player_size), rad=10, a=55)
    sq = pygame.Surface((current_player_size, current_player_size), pygame.SRCALPHA)
    bh = int(current_player_size * sq_y)
    by2 = (current_player_size - bh) // 2
    pygame.draw.rect(sq, PC, (0, by2, current_player_size, bh), border_radius=6)
    pygame.draw.rect(sq, PC2, (4, by2+4, current_player_size-8, bh-8), border_radius=4)
    pygame.draw.circle(sq, W2, (current_player_size//2, by2+bh//3), 4)
    pygame.draw.rect(sq, W2, (0, by2, current_player_size, bh), 2, border_radius=6)
    if jump_n == 1:
        pygame.draw.rect(sq, (255,220,0), (0, by2, current_player_size, bh), 3, border_radius=6)
    rot = pygame.transform.rotate(sq, -prot)
    s.blit(rot, rot.get_rect(center=(cx, cy)).topleft)

def prect():
    return pygame.Rect(px_+5, py_+5, current_player_size-10, current_player_size-10)

# World objects
obs = []
plat = []
coins = []

def draw_obs(s):
    for o in obs:
        tp, ox, ow, oh = o[0], o[1], o[2], o[3]
        if tp == 'S':
            for i in range(ow // 40):
                sx = ox + i*40
                glow_rect(s, SC, (int(sx), GY-oh, 40, oh), a=50)
                pts = [(sx+20, GY-oh), (sx+2, GY), (sx+38, GY)]
                pygame.draw.polygon(s, SC, pts)
                pygame.draw.polygon(s, (255,160,160), pts, 2)
        else:
            r = (int(ox), GY-oh, ow, oh)
            glow_rect(s, BC, r, a=50)
            pygame.draw.rect(s, BC, r, border_radius=4)
            pygame.draw.rect(s, BC2, (r[0]+4, r[1]+4, r[2]-8, r[3]-8), border_radius=3)
            pygame.draw.rect(s, (255,200,100), r, 2, border_radius=4)

def draw_plat(s):
    for p in plat:
        ox, oy, ow = int(p[0]), int(p[1]), int(p[2])
        PH = 22
        glow_rect(s, FC, (ox, oy, ow, PH), rad=12, a=60)
        pygame.draw.rect(s, FC, (ox, oy, ow, PH), border_radius=5)
        pygame.draw.rect(s, (175,120,255), (ox+2, oy+2, ow-4, 7), border_radius=3)
        pygame.draw.rect(s, FC2, (ox+2, oy+PH-6, ow-4, 5), border_radius=2)
        seg = max(24, ow // 3)
        for bx2 in range(ox+seg, ox+ow, seg):
            pygame.draw.line(s, (70,20,160), (bx2, oy+3), (bx2, oy+PH-3), 2)
        pygame.draw.rect(s, (210,170,255), (ox, oy, ow, PH), 2, border_radius=5)
        for dx2 in [6, ow-8]:
            pygame.draw.circle(s, (240,220,255), (ox+dx2, oy+4), 2)

def draw_coins_f(s):
    for c in coins:
        if not c[2]:
            continue
        by2 = c[1] + math.sin(c[3]) * 5
        glow_circle(s, CC, (int(c[0]), int(by2)), 13, a=70)
        pygame.draw.circle(s, CC, (int(c[0]), int(by2)), 13)
        pygame.draw.circle(s, (255,245,160), (int(c[0])-3, int(by2)-3), 6)
        pygame.draw.circle(s, (200,160,0), (int(c[0]), int(by2)), 13, 2)

def get_platform_rects():
    return [pygame.Rect(p[0], p[1], p[2], 22) for p in plat]

def orect(o):
    tp, ox, ow, oh = o[0], o[1], o[2], o[3]
    if tp == 'S':
        return pygame.Rect(ox+7, GY-oh+7, ow-14, oh-7)
    return pygame.Rect(ox, GY-oh, ow, oh)

# Generator
next_x = W + 200

def reset_gen():
    global next_x
    next_x = W + 200
    obs.clear()
    plat.clear()
    coins.clear()

def gen(score):
    global next_x
    if obs and obs[-1][1] >= W + 300:
        return
    x = next_x
    r = random.random()

    if score < 5:
        o = ('S', x, 40, 48)
    elif score < 15:
        o = [('S', x, 40, 48), ('B', x, 50, 50), ('S', x, 80, 48)][int(r*3)]
    else:
        o = [('S', x, random.randint(1,3)*40, 48),
             ('B', x, 50, 50),
             ('B', x, 80, 50),
             ('S', x, random.randint(2,4)*40, 48),
             ('B', x, 50, 50)][int(r*5)]
    obs.append(list(o))

    sky_chance = min(0.95, 0.5 + score * 0.012)
    if random.random() < sky_chance:
        layers = 1 if score < 15 else (2 if score < 35 else 3)
        height_bands = [
            random.randint(GY-115, GY-80),
            random.randint(GY-185, GY-125),
            random.randint(GY-250, GY-195),
        ]
        random.shuffle(height_bands)
        for i in range(layers):
            py2 = height_bands[i]
            pw = random.randint(75, 130)
            px2 = float(x + i*random.randint(80,160) + random.randint(-20,40))
            plat.append([px2, float(py2), pw])
            if random.random() < 0.75:
                n_coins = random.randint(1, 3)
                for ci in range(n_coins):
                    coins.append([px2+18+ci*24, float(py2-26), True, random.uniform(0, 6.28)])

    if random.random() < 0.3:
        coins.append([float(x+random.randint(50,110)), float(GY-58), True, random.uniform(0, 6.28)])

    gap = random.randint(220, 360) if score < 20 else random.randint(170, 290)
    next_x = x + gap

def move_world(spd, dt):
    global coin_n, combo, combo_t, current_player_size
    
    pr = prect()
    for o in obs:
        o[1] -= spd
    for p in plat:
        p[0] -= spd
    for c in coins:
        c[0] -= spd
        c[3] += dt * 4
        if c[2] and pygame.Rect(c[0]-13, c[1]-13, 26, 26).colliderect(pr):
            c[2] = False
            coin_n += 1
            combo += 1
            combo_t = 2.5
            current_player_size = min(MAX_PS, current_player_size + SIZE_PER_COIN)
            
            try:
                eat_sound.play()
            except:
                pass
            
            explode(int(c[0]), int(c[1]), [CC, (255,255,180), (200,160,0)])
            emit(int(px_+current_player_size//2), int(py_+current_player_size//2), (100,255,150), n=8, life=0.3, sz=4)
    
    obs[:] = [o for o in obs if o[1] > -200]
    plat[:] = [p for p in plat if p[0] > -200]
    coins[:] = [c for c in coins if c[0] > -60]
    return any(orect(o).colliderect(pr) for o in obs)

# Background
stars = [(random.randint(0,W), random.randint(0,GY-20), random.uniform(0.5,2)) for _ in range(80)]
clouds = [[float(random.randint(0,W)), float(random.randint(30,GY//2-30)), random.uniform(0.4,1.4), random.randint(70,150)] for _ in range(6)]
bg_off = 0.0
bg_t = 0.0

def upd_bg(spd, dt):
    global bg_t, bg_off
    bg_t += dt
    bg_off = (bg_off + spd * 0.5) % 60
    for c in clouds:
        c[0] -= spd * c[2] * 0.35
        if c[0] < -200:
            c[0] = float(W + 100)
            c[1] = float(random.randint(30, GY//2-30))

def draw_bg(s):
    for y in range(GY):
        t = y / GY
        color = (int(lerp(SKY1[0], SKY2[0], t)),
                int(lerp(SKY1[1], SKY2[1], t)),
                int(lerp(SKY1[2], SKY2[2], t)))
        pygame.draw.line(s, color, (0, y), (W, y))
    
    for sx, sy, sz in stars:
        br = int(175 + 65 * math.sin(bg_t * 1.5 + sx))
        glow_circle(s, (br, br, int(br*0.8)), (sx, sy), max(2, int(sz*2)), a=40)
        pygame.draw.circle(s, (br, br, int(br*0.8)), (sx, sy), max(1, int(sz)))
    
    for cx, cy, _, cw in clouds:
        for ox, oy, cr in [(0,0,cw//3), (cw//4,-14,cw//4), (cw//2,0,cw//3), (-cw//4,-7,cw//5)]:
            glow_circle(s, (100,150,255), (int(cx+ox), int(cy+oy)), cr, a=30)
            pygame.draw.circle(s, W2, (int(cx+ox), int(cy+oy)), cr)
    
    pygame.draw.rect(s, GND, (0, GY, W, H-GY))
    pygame.draw.line(s, (0,255,200), (0, GY), (W, GY), 4)
    pygame.draw.line(s, GNDL, (0, GY+2), (W, GY+2), 4)
    off = int(bg_off)
    for tx in range(-60, W+60, 60):
        pygame.draw.line(s, (0,255,150,100), (tx-off, GY), (tx-off, H), 1)

# HUD
coin_n = 0

def draw_hud(s, score, spd, dist, jump_used):
    global pulse_value, rainbow_offset, coin_n
    pulse_value += 0.05
    rainbow_offset += 0.02
    
    sc_surf = FB.render(str(score), True, W2)
    lbl_surf = FS.render("SCORE", True, (220,220,220))
    pill_w = max(sc_surf.get_width(), lbl_surf.get_width()) + 28
    pill_h = sc_surf.get_height() + lbl_surf.get_height() + 14
    pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
    
    border_color = rainbow_color(rainbow_offset * 10)
    pygame.draw.rect(pill, (0,0,0,200), (0,0,pill_w,pill_h), border_radius=14)
    pygame.draw.rect(pill, border_color, (0,0,pill_w,pill_h), 3, border_radius=14)
    
    pill.blit(sc_surf, ((pill_w-sc_surf.get_width())//2, 6))
    pill.blit(lbl_surf, ((pill_w-lbl_surf.get_width())//2, 8+sc_surf.get_height()))
    s.blit(pill, (12, 10))
    
    jy = 10 + pill_h + 8
    for ji in range(2):
        bx2 = 14 + ji*26
        active = ji < (2 - jump_used)
        if active:
            pulse = 1 + math.sin(pulse_value * 10 + ji) * 0.3
            size = int(18 * pulse)
            pygame.draw.rect(s, (60,220,130), (bx2, jy, size, 10), border_radius=5)
            glow_rect(s, (60,220,130), (bx2-2, jy-2, size+4, 14), rad=4, a=40)
        else:
            pygame.draw.rect(s, (130,110,90), (bx2, jy, 18, 10), border_radius=5)
    s.blit(FS.render("JUMP", True, (200,185,160)), (14, jy+13))
    
    cn_surf = FM.render(f"× {coin_n}", True, W2)
    cp_w = cn_surf.get_width() + 44
    cp = pygame.Surface((cp_w, 38), pygame.SRCALPHA)
    
    for i in range(38):
        t = i/38
        color = (int(lerp(50,30,t)), int(lerp(40,20,t)), int(lerp(20,10,t)), 200)
        pygame.draw.line(cp, color, (0,i), (cp_w,i))
    
    pygame.draw.rect(cp, CC, (0,0,cp_w,38), 2, border_radius=19)
    pygame.draw.circle(cp, CC, (20,19), 11)
    pygame.draw.circle(cp, (255,245,160), (16,15), 5)
    cp.blit(cn_surf, (36, (38-cn_surf.get_height())//2))
    s.blit(cp, (W-cp_w-12, 10))
    
    speed_color = (20,140,100) if spd < 1.5 else (200,100,20) if spd < 2.0 else (255,30,30)
    spd_surf = FS.render(f"⚡ SPD  {spd:.1f}x ⚡", True, W2)
    st = pygame.Surface((spd_surf.get_width()+16, spd_surf.get_height()+8), pygame.SRCALPHA)
    pygame.draw.rect(st, (*speed_color,190), (0,0,st.get_width(),st.get_height()), border_radius=8)
    st.blit(spd_surf, (8,4))
    s.blit(st, (W-st.get_width()-12, 54))
    
    if current_player_size > MIN_PS:
        bar_width = 120
        bar_height = 8
        bar_x = W - bar_width - 12
        bar_y = 92
        fill = int(bar_width * (current_player_size - MIN_PS) / (MAX_PS - MIN_PS))
        pygame.draw.rect(s, (40,40,40), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
        pygame.draw.rect(s, (100,255,100), (bar_x, bar_y, fill, bar_height), border_radius=4)
        size_text = FS.render(f"SIZE {current_player_size}", True, (150,255,150))
        s.blit(size_text, (bar_x - 55, bar_y - 2))
    
    if combo_t > 0 and combo > 1:
        alpha = min(255, int(combo_t/2.5*255))
        scale = 1 + (2.5 - combo_t) * 0.2
        cs = FM.render(f"✦ COMBO ×{combo} ✦", True, (255,230,60))
        cs = pygame.transform.scale(cs, (int(cs.get_width()*scale), int(cs.get_height()*scale)))
        cs.set_alpha(alpha)
        s.blit(cs, (W//2 - cs.get_width()//2, H-52))
        
        for i in range(8):
            angle = combo_t * 20 + i * 45
            x = W//2 + math.cos(angle) * 40 * scale
            y = H-45 + math.sin(angle) * 20 * scale
            pygame.draw.circle(s, (255,200,0), (int(x), int(y)), 3)
    
    bw = 360
    bx = (W - bw) // 2
    pygame.draw.rect(s, (30,20,15,180), (bx,13,bw,12), border_radius=6)
    fill = int(bw * clamp((dist % 240000) / 240000, 0, 1))
    if fill:
        for i in range(fill):
            t = i/fill
            r,g,b = int(lerp(70,255,t)), int(lerp(215,100,t)), int(lerp(135,50,t))
            pygame.draw.rect(s, (r,g,b), (bx+i,13,1,12))
    pygame.draw.rect(s, (0,255,200), (bx,13,bw,12), 2, border_radius=6)

# Menu screen
menu_t = 0.0

def draw_menu(s, best):
    global menu_t, menu_particles
    menu_t += 1/FPS
    
    if random.random() < 0.3:
        menu_particles.append([random.randint(0,W), random.randint(0,H), 
                               random.uniform(-1,1), random.uniform(-1,1), 
                               random.uniform(2,6), random.randint(100,200)])
    
    for p in menu_particles[:]:
        p[0] += p[2]
        p[1] += p[3]
        p[4] -= 0.05
        if p[4] <= 0 or p[0] < -50 or p[0] > W+50 or p[1] < -50 or p[1] > H+50:
            menu_particles.remove(p)
    
    for p in menu_particles:
        alpha = int(p[4]/6 * 255)
        color_val = (100, 200, 255)
        glow_circle(s, color_val, (int(p[0]), int(p[1])), int(p[4]), a=alpha//3)
    
    bw, bh = 700, 200
    bx = (W - bw) // 2
    by2 = 60
    rib = pygame.Surface((bw, bh), pygame.SRCALPHA)
    
    for i in range(bh):
        r = int(lerp(100, 255, (math.sin(menu_t)*0.5+0.5)))
        g = int(lerp(50, 150, (math.cos(menu_t*1.3)*0.5+0.5)))
        b = int(lerp(200, 50, (math.sin(menu_t*1.8)*0.5+0.5)))
        pygame.draw.line(rib, (r,g,b,215), (0,i), (bw,i))
    
    for d in range(-bh, bw, 38):
        pygame.draw.line(rib, (255,255,255,30), (max(0,d),0), (min(bw,d+bh),bh), 16)
    
    pygame.draw.rect(rib, (100, 200, 255), (0,0,bw,bh), 4)
    s.blit(rib, (bx, by2))
    
    title_text = "GEOMETRY"
    title_text2 = "DASH"
    for offset, dy, col in [(4,4,(50,20,10)), (3,3,(100,50,20)), (2,2,(200,100,40)), (1,1,(0,255,200)), (0,0,(255,255,255))]:
        ts = TITLE_FONT.render(title_text, True, col)
        s.blit(ts, (bx+(bw-ts.get_width())//2+offset, by2+20+dy))
        ts2 = TITLE_FONT.render(title_text2, True, col)
        s.blit(ts2, (bx+(bw-ts2.get_width())//2+offset, by2+90+dy))
    
    txt(s, FM, "★  N E O N   R U S H  ★", (0,255,200), W//2, by2+165)
    
    bcy = GY-70 + int(math.sin(menu_t*3)*22)
    for i in range(5):
        trail_x = W//2 - int(math.sin(menu_t*8 + i) * 10)
        trail_y = bcy + i * 3
        glow_circle(s, (0,255,200), (trail_x, trail_y), 10-i, a=60)
        pygame.draw.circle(s, (0,255,180), (trail_x, trail_y), 8-i)
    
    cube = pygame.Surface((50,50), pygame.SRCALPHA)
    pygame.draw.rect(cube, (0,255,180), (0,0,50,50), border_radius=10)
    pygame.draw.rect(cube, (0,200,140), (6,6,38,38), border_radius=6)
    pygame.draw.circle(cube, (255,255,255), (25,20), 6)
    pygame.draw.rect(cube, (0,255,200), (0,0,50,50), 4, border_radius=10)
    rc = pygame.transform.rotate(cube, -int(menu_t*130) % 360)
    s.blit(rc, rc.get_rect(center=(W//2, bcy)).topleft)
    
    tips = ["✨ COLLECT COINS TO GROW! ✨", "⚡ DOUBLE JUMP = MORE AIR TIME ⚡", "💎 COMBO = HIGHER SCORE! 💎"]
    for i, tip in enumerate(tips):
        y = H - 100 + math.sin(menu_t * 2 + i) * 8
        txt(s, FS, tip, (0,255,200), W//2 + i*100 - 100, y)
    
    if best > 0:
        bdg = pygame.Surface((300,55), pygame.SRCALPHA)
        pygame.draw.rect(bdg, (255,215,0,210), (0,0,300,55), border_radius=28)
        pygame.draw.rect(bdg, (0,255,200), (0,0,300,55), 3, border_radius=28)
        s.blit(bdg, ((W-300)//2, by2+210))
        
        for i in range(3):
            angle = menu_t * 8 + i * 120
            star_x = (W-300)//2 + 30 + math.sin(angle) * 5
            star_y = by2+237 + math.cos(angle*1.5) * 3
            pygame.draw.circle(s, (255,255,100), (int(star_x), int(star_y)), 6)
        
        txt(s, FM, f"🏆  BEST: {best}  🏆", (255,255,200), W//2, by2+237)
    
    p = 1 + math.sin(menu_t*4) * 0.1
    bw2 = int(420 * p)
    bh2 = int(65 * p)
    btn = pygame.Surface((bw2, bh2), pygame.SRCALPHA)
    
    for i in range(4):
        glow_color = (0,255,200, 100 - i*25)
        pygame.draw.rect(btn, glow_color, (i*4,i*4,bw2-i*8,bh2-i*8), border_radius=33)
    
    pygame.draw.rect(btn, (0,200,150,240), (0,0,bw2,bh2), border_radius=33)
    pygame.draw.rect(btn, (0,255,200), (0,0,bw2,bh2), 4, border_radius=33)
    
    bs = FM.render("▶  PRESS  SPACE  TO  PLAY  ◀", True, (255,255,255))
    btn.blit(bs, ((bw2-bs.get_width())//2, (bh2-bs.get_height())//2))
    s.blit(btn, ((W-bw2)//2, H-140))
    
    txt(s, FS, "⚡ SPACE/Click = Jump  |  MID-AIR = DOUBLE JUMP  |  ESC = Quit ⚡", (0,200,150), W//2, H-35)

# Game over screen
death_t = 0.0
death_timer = 0.0

def draw_death(s, score, best, coins_got):
    global death_timer
    death_timer += 1/FPS
    
    s.fill((0,0,0))
    
    pw, ph = 800, 480
    px, py = (W-pw)//2, (H-ph)//2
    
    pygame.draw.rect(s, (30,30,50), (px, py, pw, ph), border_radius=20)
    pygame.draw.rect(s, (0,255,200), (px, py, pw, ph), 4, border_radius=20)
    
    go_font = pygame.font.Font(None, 100)
    go_text = go_font.render("GAME OVER", True, (255,255,255))
    s.blit(go_text, (W//2 - go_text.get_width()//2, py+40))
    
    box1 = pygame.Rect(px+50, py+130, 200, 100)
    pygame.draw.rect(s, (20,20,40), box1, border_radius=15)
    pygame.draw.rect(s, (0,255,200), box1, 3, border_radius=15)
    dist_text = FS.render("DISTANCE", True, (200,200,220))
    s.blit(dist_text, (box1.centerx - dist_text.get_width()//2, box1.y + 20))
    dist_val = FM.render(f"{score} m", True, (0,255,200))
    s.blit(dist_val, (box1.centerx - dist_val.get_width()//2, box1.y + 60))
    
    box2 = pygame.Rect(px+300, py+130, 200, 100)
    pygame.draw.rect(s, (20,20,40), box2, border_radius=15)
    pygame.draw.rect(s, (255,200,0), box2, 3, border_radius=15)
    best_text = FS.render("BEST", True, (200,200,220))
    s.blit(best_text, (box2.centerx - best_text.get_width()//2, box2.y + 20))
    best_val = FM.render(str(best), True, (255,200,0))
    s.blit(best_val, (box2.centerx - best_val.get_width()//2, box2.y + 60))
    
    box3 = pygame.Rect(px+550, py+130, 200, 100)
    pygame.draw.rect(s, (20,20,40), box3, border_radius=15)
    pygame.draw.rect(s, (255,200,0), box3, 3, border_radius=15)
    coins_text = FS.render("COINS", True, (200,200,220))
    s.blit(coins_text, (box3.centerx - coins_text.get_width()//2, box3.y + 20))
    coins_val = FM.render(str(coins_got), True, (255,200,0))
    s.blit(coins_val, (box3.centerx - coins_val.get_width()//2, box3.y + 60))
    
    bonus_w = 330
    bonus_x = px+50
    bonus_y = py+260
    pygame.draw.rect(s, (20,20,40), (bonus_x, bonus_y, bonus_w, 90), border_radius=15)
    pygame.draw.rect(s, (255,200,50), (bonus_x, bonus_y, bonus_w, 90), 3, border_radius=15)
    bonus_label = FS.render("BONUS COINS", True, (255,200,50))
    s.blit(bonus_label, (bonus_x + bonus_w//2 - bonus_label.get_width()//2, bonus_y + 20))
    bonus_val = FM.render(f"+ {coins_got * 2}", True, (255,200,50))
    s.blit(bonus_val, (bonus_x + bonus_w//2 - bonus_val.get_width()//2, bonus_y + 55))
    
    final_w = 330
    final_x = px + pw - 50 - final_w
    final_y = py + 260
    pygame.draw.rect(s, (20,20,40), (final_x, final_y, final_w, 90), border_radius=15)
    pygame.draw.rect(s, (0,255,200), (final_x, final_y, final_w, 90), 3, border_radius=15)
    final_label = FS.render("FINAL HAUL", True, (0,255,200))
    s.blit(final_label, (final_x + final_w//2 - final_label.get_width()//2, final_y + 20))
    final_total = score + (coins_got * 10)
    final_val = FM.render(str(final_total), True, (0,255,200))
    s.blit(final_val, (final_x + final_w//2 - final_val.get_width()//2, final_y + 55))
    
    if death_timer > 0.8:
        pulse = 1 + math.sin(death_timer * 5) * 0.05
        btn_w = int(340 * pulse)
        btn_h = int(55 * pulse)
        btn_x = (W - btn_w) // 2
        btn_y = py + 379
        
        pygame.draw.rect(s, (0,180,130), (btn_x, btn_y, btn_w, btn_h), border_radius=30)
        pygame.draw.rect(s, (0,255,200), (btn_x, btn_y, btn_w, btn_h), 3, border_radius=30)
        
        btn_text = FM.render("▶  COLLECT REWARD  ◀", True, (255,255,255))
        s.blit(btn_text, (btn_x + btn_w//2 - btn_text.get_width()//2, btn_y + btn_h//2 - btn_text.get_height()//2))
        txt(s, FS, "Press SPACE or Click to continue", (0,255,200), W//2, btn_y + btn_h + 25)

# Main state
STATE = "menu"
score = coin_n = best = 0
spd = SPD0
dist = 0.0
jump_n_hud = 0

def new_game():
    global score, coin_n, spd, dist, death_t, death_timer, alive, jump_n_hud, current_player_size
    score = 0
    coin_n = 0
    spd = SPD0
    dist = 0.0
    death_t = 0.0
    death_timer = 0.0
    alive = True
    jump_n_hud = 0
    current_player_size = PS
    parts.clear()
    reset_player()
    reset_gen()

# Main loop
running = True
while running:
    dt = min(clock.tick(FPS) / 1000, 0.05)

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False
            elif STATE == "menu":
                STATE = "play"
                new_game()
            elif STATE == "play":
                do_jump()
            elif STATE == "dead" and death_timer > 0.8:
                STATE = "play"
                new_game()
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if STATE == "menu":
                STATE = "play"
                new_game()
            elif STATE == "play":
                do_jump()
            elif STATE == "dead" and death_timer > 0.8:
                STATE = "play"
                new_game()

    upd_bg(spd if STATE == "play" else 2.0, dt)

    if STATE == "play":
        spd = min(SPMAX, spd + SINC)
        plat_rects = get_platform_rects()
        upd_player(dt, plat_rects)

        jump_n_hud = jump_n
        gen(score)

        hit = move_world(spd, dt)
        dist += spd
        score = int(dist / 80)

        if score > best:
            best = score

        if hit:
            try:
                gameover_sound.play()
            except:
                pass
            explode(int(px_+current_player_size//2), int(py_+current_player_size//2), [PC, SC, W2, (255,200,0)])
            alive = False
            STATE = "dead"
            death_timer = 0.0

    if STATE == "dead":
        death_timer += dt

    draw_bg(screen)

    if STATE != "menu":
        draw_plat(screen)
        draw_obs(screen)
        draw_coins_f(screen)

        if STATE == "play" and alive:
            draw_player(screen)

        upd_parts(screen, dt)
        draw_hud(screen, score, spd/SPD0, dist, jump_n_hud)

    if STATE == "menu":
        draw_menu(screen, best)
    elif STATE == "dead":
        draw_death(screen, score, best, coin_n)

    pygame.display.flip()

pygame.quit()