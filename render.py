import os
from glob import glob
from PIL import Image, ImageDraw, ImageFont
# ↓ imports corrigidos ↓
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip        import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

from tqdm import tqdm

try:
    from moviepy.video.fx.resize import resize
    USE_RESIZE_FX = True
except ImportError:
    USE_RESIZE_FX = False


# ————— CONFIGURAÇÃO —————
BASE_IMG      = "templates/design_puro.png"
FONTE_PATH    = "fonts/FjallaOne-Regular.ttf"
TWEMOJI_DIR   = "fonts/twemoji"  # onde salvar os PNGs dos emojis
VIDEOS_GLOB   = "videos/*.mp4"
OUTPUT_DIR    = "output"
TOP_TEXT      = '\"Apagou a luz... e começou o pesadelo!\" 😳💤📱'
BOTTOM_TEXT   = '@KwaiZadaBrabaOfc'
COLOR_TOP     = (173, 255,  47)  # verde-lima
COLOR_BOTTOM  = (255, 255, 255)  # branco
BG_BOTTOM     = (200,  40,  40)  # vermelho escuro
# ————————————————

def render_one(video_path, top_text, bottom_text, out_path):
    bg = Image.open(BASE_IMG).convert("RGBA")
    W, H = bg.size
    draw = ImageDraw.Draw(bg)

    size_top    = int(H * 0.04)  # metade do tamanho anterior
    size_bot    = int(H * 0.05)  # levemente menor
    fnt_top     = ImageFont.truetype(FONTE_PATH, size=size_top)
    fnt_bot     = ImageFont.truetype(FONTE_PATH, size=size_bot)

    # Função para baixar PNG do Twemoji
    import requests
    def emoji_to_codepoint(emoji):
        return '-'.join(f'{ord(c):x}' for c in emoji)

    def get_emoji_img(emoji, size):
        os.makedirs(TWEMOJI_DIR, exist_ok=True)
        code = emoji_to_codepoint(emoji)
        path = os.path.join(TWEMOJI_DIR, f"{code}.png")
        if not os.path.exists(path):
            url = f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/{code}.png"
            r = requests.get(url)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    f.write(r.content)
            else:
                return None
        try:
            img = Image.open(path).convert("RGBA")
            # Redimensiona para altura da linha de texto
            ratio = size / img.height
            img = img.resize((int(img.width * ratio), size), Image.LANCZOS)
            return img
        except Exception:
            return None

    # Texto superior (com Pillow >=10) com quebra de linha automática
    import textwrap
    max_width = int(W * 0.90)
    # Quebra o texto sem dividir palavras
    def wrap_text(text, font, max_width):
        lines = []
        for paragraph in text.split('\n'):
            line = ''
            for word in paragraph.split(' '):
                test_line = line + (' ' if line else '') + word
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] <= max_width:
                    line = test_line
                else:
                    if line:
                        lines.append(line)
                    line = word
            if line:
                lines.append(line)
        return lines

    # Função para desenhar texto misturando fonte normal e emoji
    import unicodedata
    def is_emoji(char):
        # Simples: emojis estão em categorias "So" ou em alguns blocos conhecidos
        return unicodedata.category(char) == "So" or ord(char) > 0x1F000

    def draw_text_mixed_img(bg, draw, pos, text, font, fill, emoji_size):
        x, y = pos
        for char in text:
            if is_emoji(char):
                img = get_emoji_img(char, emoji_size)
                if img:
                    bg.alpha_composite(img, (int(x), int(y)))
                    x += img.width
                else:
                    # fallback: desenha como texto
                    w = draw.textbbox((0, 0), char, font=font)[2]
                    draw.text((x, y), char, font=font, fill=fill)
                    x += w
            else:
                w = draw.textbbox((0, 0), char, font=font)[2]
                draw.text((x, y), char, font=font, fill=fill)
                x += w
        return x

    top_lines = wrap_text(top_text, fnt_top, max_width)
    total_h = 0
    line_heights = []
    for line in top_lines:
        _, _, _, y1 = draw.textbbox((0, 0), line, font=fnt_top)
        h = y1
        line_heights.append(h)
        total_h += h
    y_top = int(H * 0.12)  # desce mais o texto superior
    curr_y = y_top
    for i, line in enumerate(top_lines):
        # Calcula largura considerando mistura de fontes e emojis
        w = 0
        for c in line:
            if is_emoji(c):
                img = get_emoji_img(c, size_top)
                w += img.width if img else draw.textbbox((0, 0), c, font=fnt_top)[2]
            else:
                w += draw.textbbox((0, 0), c, font=fnt_top)[2]
        x = (W - w) // 2
        draw_text_mixed_img(bg, draw, (x, curr_y), line, fnt_top, COLOR_TOP, size_top)
        curr_y += line_heights[i]

    # Faixa inferior + texto, mais alta e arredondada
    x0b, y0b, x1b, y1b = draw.textbbox((0, 0), bottom_text, font=fnt_bot)
    w_bot = x1b - x0b
    h_bot = y1b - y0b
    pad_x = int(W * 0.03)
    pad_y = int(H * 0.015)
    rect_w = w_bot + 2*pad_x
    rect_h = h_bot + 2*pad_y
    x_rect = (W - rect_w) // 2
    # Sobe a faixa vermelha
    y_rect = int(H * 0.72)
    radius = int(rect_h * 0.3)
    # Desenha retângulo arredondado
    try:
        draw.rounded_rectangle([x_rect, y_rect, x_rect+rect_w, y_rect+rect_h], radius=radius, fill=BG_BOTTOM)
    except AttributeError:
        # Pillow < 8.2 não tem rounded_rectangle
        draw.rectangle([x_rect, y_rect, x_rect+rect_w, y_rect+rect_h], fill=BG_BOTTOM)
    # Desenha texto inferior misturando fonte normal e emoji
    draw_text_mixed_img(bg, draw, (x_rect+pad_x, y_rect+pad_y), bottom_text, fnt_bot, COLOR_BOTTOM, size_bot)

    # Salva a imagem final (moldura)
    out_img = out_path.replace('.mp4', '_onlyimg.png')
    bg.save(out_img)

    # --- INSERE O VÍDEO CENTRALIZADO NA ÁREA PRETA DA MOLDURA ---
    # Descobre a área preta (moldura) na imagem base
    # Ajuste exato da faixa preta conforme medições do Canva
    faixa_h = 850
    faixa_w = bg.width
    # Centraliza a faixa preta verticalmente
    faixa_top = (bg.height - faixa_h) // 2
    faixa_bot = faixa_top + faixa_h

    # Carrega o vídeo
    clip_vid = VideoFileClip(video_path)
    # Redimensiona o vídeo para caber na faixa preta (sem ultrapassar)
    # Mantém proporção e nunca ultrapassa a faixa preta
    if (clip_vid.h / faixa_h) > (clip_vid.w / faixa_w):
        # vídeo é mais "alto" que a faixa: limita pela altura
        if hasattr(clip_vid, 'resize'):
            clip_vid_resized = clip_vid.resize(height=faixa_h)
        else:
            clip_vid_resized = clip_vid.resized(height=faixa_h)
    else:
        # vídeo é mais "largo" que a faixa: limita pela largura
        if hasattr(clip_vid, 'resize'):
            clip_vid_resized = clip_vid.resize(width=faixa_w)
        else:
            clip_vid_resized = clip_vid.resized(width=faixa_w)
    # Centraliza o vídeo na faixa preta
    new_w, new_h = clip_vid_resized.size
    x_center = (bg.width - new_w) // 2
    y_center = faixa_top + (faixa_h - new_h) // 2 - 30

    # Cria um clip da moldura (imagem) com duração compatível
    clip_bg = ImageClip(out_img)
    if hasattr(clip_bg, 'set_duration'):
        clip_bg = clip_bg.set_duration(clip_vid.duration)
    else:
        clip_bg = clip_bg.with_duration(clip_vid.duration)
    # Posiciona o vídeo sobre a moldura
    if hasattr(clip_vid_resized, 'set_position'):
        clip_vid_resized = clip_vid_resized.set_position((x_center, y_center))
    else:
        clip_vid_resized = clip_vid_resized.with_position((x_center, y_center))
    comp = CompositeVideoClip([clip_bg, clip_vid_resized])
    comp.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=clip_vid.fps, threads=4)

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for vid in tqdm(glob(VIDEOS_GLOB), desc="Renderizando"):
        name = os.path.splitext(os.path.basename(vid))[0]
        out  = os.path.join(OUTPUT_DIR, f"{name}_final.mp4")
        render_one(vid, TOP_TEXT, BOTTOM_TEXT, out)
