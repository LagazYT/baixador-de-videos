"""
Arte do Baixador de Vídeos: escolhe entre os estilos visuais do aplicativo.

- "classico"  -> arte_classico.py (roxo e rosa, cantos arredondados) - padrão
- "cyberpunk" -> arte_cyber.py    (amarelo, vermelho e cinza, cantos chanfrados)
- "retro"     -> arte_retro.py    (creme, laranja, mostarda e verde-petróleo, minimalista)
- "steampunk" -> arte_steam.py    (latão, cobre e madeira, com engrenagens e manômetro)
- "arcade"    -> arte_arcade.py   (pixel art de fliperama: estrelas, moedas e corações)
- "rpg"       -> arte_rpg.py      (fantasia: castelo, selo dourado, escudo e baú)

Rodar `python arte.py` gera o icone.ico, as imagens do instalador e os ícones da
extensão do navegador (sempre no estilo clássico, que é o visual principal).
"""
import arte_classico
import arte_cyber
import arte_retro
import arte_steam
import arte_arcade
import arte_rpg

STYLES = {"classico": arte_classico, "cyberpunk": arte_cyber, "retro": arte_retro, "steampunk": arte_steam,
          "arcade": arte_arcade, "rpg": arte_rpg}
DEFAULT_STYLE = "classico"
_current = arte_classico


def set_style(name):
    global _current
    _current = STYLES.get(name, STYLES[DEFAULT_STYLE])


def make_icon(*args, **kwargs):
    return _current.make_icon(*args, **kwargs)


def save_ico(*args, **kwargs):
    return _current.save_ico(*args, **kwargs)


def make_banner(*args, **kwargs):
    return _current.make_banner(*args, **kwargs)


def make_footer(*args, **kwargs):
    return _current.make_footer(*args, **kwargs)


def make_placeholder(*args, **kwargs):
    return _current.make_placeholder(*args, **kwargs)


def make_empty_art(*args, **kwargs):
    return _current.make_empty_art(*args, **kwargs)


def make_wizard_large(*args, **kwargs):
    return _current.make_wizard_large(*args, **kwargs)


def make_wizard_small(*args, **kwargs):
    return _current.make_wizard_small(*args, **kwargs)


if __name__ == "__main__":
    import os

    set_style(DEFAULT_STYLE)
    save_ico("icone.ico")
    os.makedirs("instalador_assets", exist_ok=True)
    make_wizard_large().save(os.path.join("instalador_assets", "wizard_large.bmp"))
    make_wizard_small().save(os.path.join("instalador_assets", "wizard_small.bmp"))
    os.makedirs(os.path.join("extensao_navegador", "icons"), exist_ok=True)
    for n in (16, 32, 48, 128):
        make_icon(n).save(os.path.join("extensao_navegador", "icons", f"icon{n}.png"))
    print("icone.ico, imagens do instalador e icones da extensao criados.")
