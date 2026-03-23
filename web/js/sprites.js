// Sprites — string-encoded for compactness
// Character 16×32 | Furniture 16×16 | Indicators 8×8

const PALETTES = {
  direccion:      { primary:'#7F77DD', dark:'#3C3489', light:'#CECBF6' },
  desarrollo:     { primary:'#378ADD', dark:'#0C447C', light:'#B5D4F4' },
  ux_ui:          { primary:'#1D9E75', dark:'#085041', light:'#9FE1CB' },
  qa:             { primary:'#639922', dark:'#27500A', light:'#C0DD97' },
  marketing:      { primary:'#D85A30', dark:'#712B13', light:'#F5C4B3' },
  atencion:       { primary:'#BA7517', dark:'#633806', light:'#FAC775' },
  oportunidades:  { primary:'#D4537E', dark:'#72243E', light:'#F4C0D1' },
  administrativo: { primary:'#888780', dark:'#444441', light:'#D3D1C7' },
  servidores:     { primary:'#2C2C2A', dark:'#111110', light:'#6E6E6C' },
};

// Color map for string encoding
const _CM = {
  '.':null, 'D':'#2A2A3A', 'S':'#FDBCB4', 'W':'#FFFFFF', 'E':'#1A1A2A',
  'G':'G', 'H':'#5B3A29', 'B':'#1A1A2E', 'F':'#5C4033', 'f':'#8B6914',
  'M':'#3A3A4A', 'm':'#2A2A35', 'P':'#4488CC', 'g':'#22CC66',
  'R':'#CC3333', 'b':'#3355AA', 'n':'#33AA55', 'Y':'#CCAA33',
  'p':'#AA3366', 'c':'#3388AA', 'L':'#6B3A22', 'l':'#8B5A3A',
  'a':'#A0704A', 'K':'#C49A6C', 'k':'#D4AA7C', 'T':'#1B6B3A',
  't':'#228B4C', 'J':'#6699CC', 'j':'#88BBEE', 'U':'#AADDFF',
  'O':'#8B6914', 'o':'#AA8833', 'q':'#CCAA55', 'e':'#EECCAA',
  'V':'#FFEE88', 'v':'#FFDD44', 'X':'#44FF44', 'x':'#FF4444',
  'Z':'#FFAA00', 'z':'#4488FF', 'A':'#223355', 'I':'#4A2512',
};

// Parse string sprite: rows separated by |, each char = 1 pixel
function _parseSprite(str, w) {
  const rows = str.split('|');
  return rows.map(r => {
    const cols = [];
    for (let i = 0; i < w; i++) cols.push(_CM[r[i]] || null);
    return cols;
  });
}

// --- CHARACTER SPRITES 16×32 ---
const _CS = {};
_CS.char_down_0 = _parseSprite(
  '......DDDD......|.....DDDDDD.....|....DDDDDDDD....|....DDDDDDDDD...|...DDSSSSSSSDD..|...DSSWEWESSD...|...DSSSSSSSD....|...DSSSSSSD.....|....SSSSSS......|...GGGGGGGG.....|..GGGGGGGGGG....|..GGGGGGGGGG....|.GGGGGGGGGGGG...|.GGGGGGGGGGGG...|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGG.GG.GGG....|..GGG.GG.GGG....|..GGG....GGG....|..GGG....GGG....|..GGG....GGG....|...SS....SS.....|...SS....SS.....|...SS....SS.....|...SS....SS.....|...DD....DD.....|...DD....DD.....|...DD....DD.....|...DDD..DDD.....|................|................', 16);

_CS.char_down_1 = _parseSprite(
  '......DDDD......|.....DDDDDD.....|....DDDDDDDD....|....DDDDDDDDD...|...DDSSSSSSSDD..|...DSSWEWESSD...|...DSSSSSSSD....|...DSSSSSSD.....|....SSSSSS......|...GGGGGGGG.....|..GGGGGGGGGG....|..GGGGGGGGGG....|.GGGGGGGGGGGG...|.GGGGGGGGGGGG...|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGG.GG.GGG....|..GGG.GG.GGG....|..GGG....GGG....|..GGG....GGG....|...SS.....GG....|...SS....SS.....|...S.....SS.....|...DD....SS.....|........DD......|........DD......|........DDD.....|................|................|................|................', 16);

_CS.char_up_0 = _parseSprite(
  '......DDDD......|.....DDDDDD.....|....DDDDDDDD....|....DDDDDDDDD...|...DDDDDDDDDDD..|...DDDDDDDDD....|...DDDDDDDDD....|...DDDDDDDD.....|....SSSSSS......|...GGGGGGGG.....|..GGGGGGGGGG....|..GGGGGGGGGG....|.GGGGGGGGGGGG...|.GGGGGGGGGGGG...|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGG.GG.GGG....|..GGG.GG.GGG....|..GGG....GGG....|..GGG....GGG....|..GGG....GGG....|...SS....SS.....|...SS....SS.....|...SS....SS.....|...SS....SS.....|...DD....DD.....|...DD....DD.....|...DD....DD.....|...DDD..DDD.....|................|................', 16);

_CS.char_up_1 = _parseSprite(
  '......DDDD......|.....DDDDDD.....|....DDDDDDDD....|....DDDDDDDDD...|...DDDDDDDDDDD..|...DDDDDDDDD....|...DDDDDDDDD....|...DDDDDDDD.....|....SSSSSS......|...GGGGGGGG.....|..GGGGGGGGGG....|..GGGGGGGGGG....|.GGGGGGGGGGGG...|.GGGGGGGGGGGG...|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGG.GG.GGG....|..GGG.GG.GGG....|..GG.....GGG....|...GG....GGG....|...SS....SS.....|..SS.....SS.....|..SS....DD......|..DD....DD......|..DD............|..DDD...........|................|................|................|................|................', 16);

_CS.char_left_0 = _parseSprite(
  '......DDDD......|.....DDDDD......|....DDDDDD......|....DDDDDDD.....|...DDSSSSD......|...WESDSD.......|...SSSSS........|....SSS.........|....SSSS........|...GGGGGGG......|..GGGGGGGG......|..GGGGGGGGG.....|..GGGGGGGGG.....|..GGGGGGGG......|...GGGGGGG......|...GGGGGG.......|...GGGGG........|...GGGGG........|....GGGG........|....GGG.........|....GGG.........|....SS..........|....SS..........|....SS..........|...SS...........|...DD...........|...DD...........|...DD...........|...DDD..........|................|................|................', 16);

_CS.char_left_1 = _parseSprite(
  '......DDDD......|.....DDDDD......|....DDDDDD......|....DDDDDDD.....|...DDSSSSD......|...WESDSD.......|...SSSSS........|....SSS.........|....SSSS........|...GGGGGGG......|..GGGGGGGG......|..GGGGGGGGG.....|..GGGGGGGGG.....|..GGGGGGGG......|...GGGGGGG......|...GGGGGG.......|...GGGGG........|...GGG.GG.......|....GG..GG......|...SS...GG......|...S....SS......|...DD...SS......|..........S.....|..........D.....|..........D.....|..........DD....|................|................|................|................|................|................', 16);

_CS.char_sit = _parseSprite(
  '......DDDD......|.....DDDDDD.....|....DDDDDDDD....|....DDDDDDDDD...|...DDSSSSSSSDD..|...DSSWEWESSD...|...DSSSSSSSD....|...DSSSSSSD.....|....SSSSSS......|...GGGGGGGG.....|..GGGGGGGGGG....|..GGGGGGGGGG....|.GGGGGGGGGGGG...|.GGGGGGGGGGGG...|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGGGGGGGGG....|.GGGGGGGGGGGGG..|..GGGGGGGGGGG...|....SSSSSS......|....SS..SS......|....DD..DD......|................|................|................|................|................|................|................|................|................|................', 16);

_CS.char_type_0 = _parseSprite(
  '......DDDD......|.....DDDDDD.....|....DDDDDDDD....|....DDDDDDDDD...|...DDSSSSSSSDD..|...DSSWEWESSD...|...DSSSSSSSD....|...DSSSSSSD.....|....SSSSSS......|...GGGGGGGG.....|..GGGGGGGGGG....|..GGGGGGGGGG....|.GGGGGGGGGGGG...|.GGGGGGGGGGGG...|..GGGGGGGGGG....|.SGGGGGGGGGGS...|.SGGGGGGGGGGS...|.GGGGGGGGGGGGG..|..GGGGGGGGGGG...|....SSSSSS......|....SS..SS......|....DD..DD......|................|................|................|................|................|................|................|................|................|................', 16);

_CS.char_type_1 = _parseSprite(
  '......DDDD......|.....DDDDDD.....|....DDDDDDDD....|....DDDDDDDDD...|...DDSSSSSSSDD..|...DSSWEWESSD...|...DSSSSSSSD....|...DSSSSSSD.....|....SSSSSS......|...GGGGGGGG.....|..GGGGGGGGGG....|..GGGGGGGGGG....|.GGGGGGGGGGGG...|.GGGGGGGGGGGG...|..GGGGGGGGGG....|..GGGGGGGGGG....|.SGGGGGGGGGGS...|.SGGGGGGGGGGGS..|..GGGGGGGGGGG...|....SSSSSS......|....SS..SS......|....DD..DD......|................|................|................|................|................|................|................|................|................|................', 16);

_CS.char_idle_0 = _parseSprite(
  '......DDDD......|.....DDDDDD.....|....DDDDDDDD....|....DDDDDDDDD...|...DDSSSSSSSDD..|...DSSWEWESSD...|...DSSSSSSSD....|...DSSSSSSD.....|....SSSSSS......|...GGGGGGGG.....|..GGGGGGGGGG....|..GGGGGGGGGG....|.GGGGGGGGGGGG...|.GGGGGGGGGGGG...|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGG.GG.GGG....|..GGG.GG.GGG....|..GGG....GGG....|..GGG....GGG....|..GGG....GGG....|...SS....SS.....|...SS....SS.....|...SS....SS.....|...SS....SS.....|...DD....DD.....|...DD....DD.....|...DD....DD.....|...DDD..DDD.....|................|................', 16);

_CS.char_idle_1 = _parseSprite(
  '.......DDDD.....|......DDDDDD....|.....DDDDDDDD...|.....DDDDDDDDD..|....DDSSSSSSSDD.|....DSSWEWESSD..|....DSSSSSSSD...|....DSSSSSSD....|.....SSSSSS.....|...GGGGGGGG.....|..GGGGGGGGGG....|..GGGGGGGGGG....|.GGGGGGGGGGGG...|.GGGGGGGGGGGG...|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGGGGGGGGG....|..GGG.GG.GGG....|..GGG.GG.GGG....|..GGG....GGG....|..GGG....GGG....|..GGG....GGG....|...SS....SS.....|...SS....SS.....|...SS....SS.....|...SS....SS.....|...DD....DD.....|...DD....DD.....|...DD....DD.....|...DDD..DDD.....|................|................', 16);

const SPRITES = _CS;

// --- FURNITURE SPRITES 16×16 (kept as arrays for existing compatibility) ---
const _ = null;
const F1 = '#5C4033', F2 = '#8B6914', F3 = '#3A3A4A', F4 = '#2A2A35';
const F5 = '#4488CC', F6 = '#22CC66';

const FURNITURE_SPRITES = {
  desk: _parseSprite('................|.FFFFFFFFFFFFFF.|.FfffffffffffffffF.|.FfffffffffffffffF.|.FffPPPPPPffffffffffF.|.FffPPPPPPffffffffffF.|.FffPPPPPPffffffffffF.|.FffMMMMMMffffffffffF.|.FfffffffffffffffF.|.FFFFFFFFFFFFFF.|..F..........F..|..F..........F..|................|................|................|................', 16),
  chair_down: _parseSprite('................|....MMMMMMMM....|....MmmmmmmM....|....MmmmmmmM....|....MmmmmmmM....|....MMMMMMMM....|...MmmmmmmmmM...|...MmmmmmmmmM...|...MmmmmmmmmM...|...MMMMMMMMMMM..|.....M....M.....|.....M....M.....|....M......M....|................|................|................', 16),
  chair_up: _parseSprite('................|................|....M......M....|.....M....M.....|...MMMMMMMMMMM..|...MmmmmmmmmM...|...MmmmmmmmmM...|...MmmmmmmmmM...|....MMMMMMMM....|....MmmmmmmM....|....MmmmmmmM....|....MmmmmmmM....|....MMMMMMMM....|................|................|................', 16),
  plant: _parseSprite('......ggg.......|.....ggggg......|....ggggggg.....|...gggnggggg.....|..ggngggngggg....|..gggggggggg.....|...ggngggnggg....|....ggggggg.....|.......FF.......|.......FF.......|.......FF.......|.....FFFFFF.....|....FFFFFFFFf...|....FFFFFFFFf...|.....FFFFFF.....|................', 16),
  server_rack: _parseSprite('..MMMMMMMMMMMM..|..MmmmmmmmmmmM..|..MmXmmmmmXmmM..|..MmmmmmmmmmmM..|..MMMMMMMMMMMM..|..MmmmmmmmmmmM..|..MmZmmmmmXmmM..|..MmmmmmmmmmmM..|..MMMMMMMMMMMM..|..MmmmmmmmmmmM..|..MmXmmmmmxmmM..|..MmmmmmmmmmmM..|..MMMMMMMMMMMM..|..M..........M..|..M..........M..|..MMMMMMMMMMMM..', 16),
  bookshelf: _parseSprite('.FFFFFFFFFFFFFF.|.FRRbbnnYYppccFF.|.FRRbbnnYYppccFF.|.FRRbbnnYYppccFF.|.FRRbbnnYYppccFF.|.FFFFFFFFFFFFFF.|.FbbccFFnnppFccF.|.FbbccFFnnppFccF.|.FbbccFFnnppFccF.|.FbbccFFnnppFccF.|.FFFFFFFFFFFFFF.|.FfffffffffffffffF.|.F............F.|.F............F.|.FFFFFFFFFFFFFF.|................', 16),
  water_cooler: _parseSprite('.....JJJJJJ.....|....JjjjjjjJ....|....JjUUUUjJ....|....JjjjjjjJ....|.....JJJJJJ.....|......MMMM......|.....MMmmMM.....|.....MmmmmM.....|.....MmxmmM.....|.....MmmmmM.....|.....MMMMMM.....|.....MmmmmM.....|.....MmmmmM.....|....MMMMMMMM....|....M......M....|....MMMMMMMM....', 16),
  whiteboard: _parseSprite('.MMMMMMMMMMMMMM.|.MWWWWWWWWWWWWM.|.MWWWbWWWWWWWWM.|.MWWbbbbWWWWWWM.|.MWWWbWWxWWWWWM.|.MWWWWWxxxWWWWM.|.MWWWWWWxWWWWWM.|.MWnnnnWWWWWWWM.|.MWWWWWWWnnWWWM.|.MWWWWWWWWWWWWM.|.MMMMMMMMMMMMMM.|.......MM.......|.......MM.......|.......MM.......|......MMMM......|................', 16),
  lamp: _parseSprite('.....VVVVVV.....|....VvvvvvvV....|...VvMMMMMMvV...|....VMMMMMMV....|.....MmmmmM.....|......MMMM......|.......MM.......|.......MM.......|.......MM.......|.......MM.......|......MMMM......|.....MMMMMM.....|................|................|................|................', 16),
  sofa_h: _parseSprite('................|.LLLLLLLLLLLLLL.|.LlllllLLlllllL.|.LlaaalLLlaaalL.|.LlaaalLLlaaalL.|.LlaaalLLlaaalL.|.LlllllLLlllllL.|.LLLLLLLLLLLLLL.|.LllllllllllllL.|.LllllllllllllL.|.LLLLLLLLLLLLLL.|..I..........I..|................|................|................|................', 16),
  sofa_v: _parseSprite('................|.LLLLLLLLLL.....|.LlllllllllL....|.LlaaaaaalL.....|.LlaaaaaalL.....|.LLLLLLLLLL.....|.LlllllllllL....|.LlaaaaaalL.....|.LlaaaaaalL.....|.LLLLLLLLLL.....|.LlllllllllL....|.LLLLLLLLLL.....|..I.......I.....|................|................|................', 16),
  coffee_table: _parseSprite('................|................|...FFFFFFFFFFF..|..FfffffffffffffffF.|..FfffffffffffffffF.|..FfffWWWffffffF.|..FffWOOWWffffffF.|..FffWOOOWffffffF.|..FfffWWWffffffF.|..FfffffffffffffffF.|..FfffffffffffffffF.|...FFFFFFFFFFF..|....F.....F.....|................|................|................', 16),
  tv: _parseSprite('................|.MMMMMMMMMMMMMM.|.MmmmmmmmmmmmmM.|.MmAAAAAAAAAAmM.|.MmAAAAAAAAAAmM.|.MmAAAAAAAAAAmM.|.MmAAAAAAAAAAmM.|.MmAAAAAAAAAAmM.|.MmAAAAAAAAAAmM.|.MMMMMMMMMMMMMM.|.......MM.......|.......MM.......|.....MMMMMM.....|................|................|................', 16),
  ping_pong: _parseSprite('................|.TTTTTTTTTTTTTT.|.TttttttttttttT.|.TtttttWWtttttT.|.TtttttWWtttttT.|.TtttttWWtttttT.|.TtttttWWtttttT.|.TtttttWWtttttT.|.TtttttWWtttttT.|.TttttttttttttT.|.TTTTTTTTTTTTTT.|..F..........F..|..F..........F..|................|................|................', 16),
  dog_bed: _parseSprite('................|................|....OOOOOOOO....|...OooooooooO...|..OoqqqqqqqooO..|..OoqeeeeeqoO...|..OoqeeeeeqoO...|..OoqeeeeeqoO...|..OoqeeeeeqoO...|..OoqqqqqqqooO..|...OooooooooO...|....OOOOOOOO....|................|................|................|................', 16),
  dog_idle_0: _parseSprite('................|................|................|................|...K............|..KKK...........|.KkkKKKKKKKK....|.KkEkkkkkkkkK...|..KkkkkkkkkkkK..|..KKKKKKKKKKKK..|...KK.......KK..|................|................|................|................|................', 16),
  dog_idle_1: _parseSprite('................|................|................|...K............|..KKK...........|.KkkKKKKKKKK....|.KkEkkkkkkkkK...|..KkkkkkkkkkkK..|..KKKKKKKKKKKK..|...KK.......KK..|................|................|................|................|................|................', 16),
  printer: _parseSprite('................|................|...MMMMMMMMMM...|..MMmmmmmmmmMM..|.MMmmmmmmmmmmMM.|.MmmmmmmmmmmmmM.|.MmmmmmmmmmmmmM.|.MMMMMMMMMMMMMM.|.MWWWWWWWWWWWWM.|.MWWWWWWWWWWWWM.|.MMMMMMMMMMMMMM.|..M..........M..|................|................|................|................', 16),
};

// --- INDICATOR SPRITES 8×8 ---
const INDICATOR_SPRITES = {
  ind_working:_parseSprite('..XXXX..|.XXXXXX.|XXWXXWXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|.XXXXXX.|..XXXX..', 8),
  ind_idle:   _parseSprite('..MMMM..|.MMMMMM.|MMWMMWMM|MMMMMMMM|MMMMMMMM|MMMMMMMM|.MMMMMM.|..MMMM..', 8),
  ind_waiting:_parseSprite('..ZZZZ..|.ZZZZZZ.|ZZWZZWZZ|ZZZZZZZZ|ZZZZZZZZ|ZZZZZZZZ|.ZZZZZZ.|..ZZZZ..', 8),
  ind_error:  _parseSprite('..xxxx..|.xxxxxx.|xxWxxWxx|xxxxxxxx|xxxxxxxx|xxxxxxxx|.xxxxxx.|..xxxx..', 8),
  ind_done:   _parseSprite('..zzzz..|.zzzzzz.|zzWzzWzz|zzzzzzzz|zzzzzzzz|zzzzzzzz|.zzzzzz.|..zzzz..', 8),
};

// --- Drawing functions ---
function drawSprite(ctx, spriteData, x, y, zoom) {
  for (let r = 0; r < spriteData.length; r++) {
    for (let c = 0; c < spriteData[r].length; c++) {
      if (!spriteData[r][c]) continue;
      ctx.fillStyle = spriteData[r][c];
      ctx.fillRect(Math.floor(x + c * zoom), Math.floor(y + r * zoom), zoom, zoom);
    }
  }
}

function drawCharSprite(ctx, spriteName, x, y, zoom, deptId) {
  const data = SPRITES[spriteName];
  if (!data) return;
  const palette = PALETTES[deptId] || PALETTES.administrativo;
  for (let r = 0; r < data.length; r++) {
    for (let c = 0; c < data[r].length; c++) {
      const px = data[r][c];
      if (!px) continue;
      if (px === 'G') {
        ctx.fillStyle = (c + r) % 3 === 0 ? palette.dark : palette.primary;
      } else {
        ctx.fillStyle = px;
      }
      ctx.fillRect(Math.floor(x + c * zoom), Math.floor(y + r * zoom), zoom, zoom);
    }
  }
}

function drawFurnitureSprite(ctx, name, x, y, zoom) {
  const data = FURNITURE_SPRITES[name];
  if (!data) return;
  drawSprite(ctx, data, x, y, zoom);
}

function drawIndicator(ctx, status, x, y, zoom) {
  const name = 'ind_' + status;
  const data = INDICATOR_SPRITES[name] || INDICATOR_SPRITES.ind_idle;
  const iZoom = Math.max(1, Math.floor(zoom / 2));
  drawSprite(ctx, data, x, y, iZoom);
}
