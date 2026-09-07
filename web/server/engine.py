"""Deterministic 50 Hz rules mirrored by public/engine.js. No client scores accepted."""
import copy

SHAPES = {
    'I': [(0,0),(1,0),(2,0),(3,0)], 'O': [(0,0),(1,0),(0,1),(1,1)],
    'T': [(0,0),(1,0),(2,0),(1,1)], 'S': [(1,0),(2,0),(0,1),(1,1)],
    'Z': [(0,0),(1,0),(1,1),(2,1)], 'J': [(0,0),(0,1),(1,1),(2,1)],
    'L': [(2,0),(0,1),(1,1),(2,1)],
}
ACTIONS = {'left', 'right', 'rotate', 'down', 'drop'}

class Engine:
    def __init__(self, seed=1, state=None):
        if state is not None:
            self.__dict__.update(copy.deepcopy(state))
            return
        self.rng = seed or 1
        self.board = [[None]*10 for _ in range(20)]
        self.bag = []
        self.score = self.lines = self.ticks = 0
        self.over = False
        self.next = self.take()
        self.spawn()

    def random(self):
        x = self.rng
        x ^= (x << 13) & 0xffffffff
        x ^= x >> 17
        x ^= (x << 5) & 0xffffffff
        self.rng = x & 0xffffffff
        return self.rng

    def take(self):
        if not self.bag:
            self.bag = list(SHAPES)
            for i in range(6,0,-1):
                j = self.random() % (i+1)
                self.bag[i],self.bag[j] = self.bag[j],self.bag[i]
        return self.bag.pop()

    def spawn(self):
        self.piece = self.next
        self.next = self.take()
        self.shape = [list(p) for p in SHAPES[self.piece]]
        self.x, self.y = 3, 0
        self.fall = self.contact = self.resets = 0
        if not self.fits(self.x,self.y,self.shape): self.over = True

    def fits(self,x,y,shape):
        return all(0<=x+a<10 and 0<=y+b<20 and self.board[y+b][x+a] is None for a,b in shape)

    def landing(self):
        y=self.y
        while self.fits(self.x,y+1,self.shape): y+=1
        return y

    def lock(self):
        for a,b in self.shape: self.board[self.y+b][self.x+a]=self.piece
        remaining=[r for r in self.board if None in r]
        cleared=20-len(remaining)
        self.score += [0,100,300,500,800][cleared] * (1+self.lines//10)
        self.lines += cleared
        self.board = [[None]*10 for _ in range(cleared)] + remaining
        self.spawn()

    def action(self,key):
        if self.over: return
        grounded=not self.fits(self.x,self.y+1,self.shape)
        moved=False
        if key in ('left','right'):
            dx=-1 if key=='left' else 1
            if self.fits(self.x+dx,self.y,self.shape): self.x+=dx; moved=True
        elif key=='rotate' and self.piece!='O':
            rotated=[[-b,a] for a,b in self.shape]
            mx=min(a for a,b in rotated); my=min(b for a,b in rotated)
            rotated=[[a-mx,b-my] for a,b in rotated]
            for dx,dy in ((0,0),(-1,0),(1,0),(-2,0),(2,0),(0,-1),(0,-2)):
                if self.fits(self.x+dx,self.y+dy,rotated):
                    self.x+=dx;self.y+=dy;self.shape=rotated;moved=True;break
        elif key=='down':
            if self.fits(self.x,self.y+1,self.shape): self.y+=1;self.fall=0
        elif key=='drop':
            self.y=self.landing();self.lock();return
        if moved and grounded and self.resets<15: self.contact=0;self.resets+=1

    def step(self, actions=()):
        self.ticks+=1
        if self.over: return
        for key in actions: self.action(key)
        if self.over: return
        self.fall+=1
        delay=max(6,40-(self.lines//10)*3)
        if self.fall>=delay:
            self.fall=0
            if self.fits(self.x,self.y+1,self.shape): self.y+=1
        if self.fits(self.x,self.y+1,self.shape): self.contact=0
        else:
            self.contact+=1
            if self.contact>=20: self.lock()

    def export(self): return copy.deepcopy(self.__dict__)
