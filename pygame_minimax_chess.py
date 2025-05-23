import pygame
import chess
import time
import sys
import os
from minimax_chess import get_minimax_move

# When frozen by PyInstaller, assets are unpacked into sys._MEIPASS
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(__file__)


def asset_path(rel_path):
    return os.path.join(BASE_DIR, rel_path)


SQUARE_SIZE = 80
BOARD_PIXELS = SQUARE_SIZE * 8
CAPTURE_HEIGHT = SQUARE_SIZE // 2
LABEL_FONT_SIZE = 30
LABEL_MARGIN = LABEL_FONT_SIZE
TOP_MARGIN = LABEL_MARGIN + CAPTURE_HEIGHT
BOTTOM_MARGIN = CAPTURE_HEIGHT + LABEL_MARGIN
WINDOW_WIDTH = BOARD_PIXELS
WINDOW_HEIGHT = TOP_MARGIN + BOARD_PIXELS + BOTTOM_MARGIN
DOT_RADIUS = 16
ENGINE_FONT_SIZE = 24
FPS = 120


def load_images():
    imgs = {}
    for color in ["w", "b"]:
        for p in ["P", "N", "B", "R", "Q", "K"]:
            raw = pygame.image.load(asset_path(f"assets/{color}{p}.png"))
            imgs[f"{color}{p}"] = pygame.transform.smoothscale(
                raw, (SQUARE_SIZE, SQUARE_SIZE)
            )
    return imgs


def board_to_screen(sq, orient_white):
    file = chess.square_file(sq)
    rank = chess.square_rank(sq)

    if orient_white:
        sf = file
        sr = 7 - rank
    else:
        sf = 7 - file
        sr = rank
    x = sf * SQUARE_SIZE
    y = sr * SQUARE_SIZE + TOP_MARGIN

    return x, y


def screen_to_board(pos, orient_white):
    mx, my = pos

    if not (TOP_MARGIN <= my < TOP_MARGIN + BOARD_PIXELS):
        return None

    sf = mx // SQUARE_SIZE
    sr = (my - TOP_MARGIN) // SQUARE_SIZE

    if not (0 <= sf < 8 and 0 <= sr < 8):
        return None

    if orient_white:
        file = sf
        rank = 7 - sr
    else:
        file = 7 - sf
        rank = sr

    return chess.square(file, rank)


def draw_board(screen):
    light = pygame.Color(240, 217, 181)
    dark = pygame.Color(181, 136, 99)

    for r in range(8):
        for f in range(8):
            rect = pygame.Rect(
                f * SQUARE_SIZE,
                r * SQUARE_SIZE + TOP_MARGIN,
                SQUARE_SIZE,
                SQUARE_SIZE,
            )

            pygame.draw.rect(screen, light if (r + f) % 2 == 0 else dark, rect)


def draw_labels(screen, orient_white):
    font = pygame.font.SysFont(None, LABEL_FONT_SIZE)
    files = "abcdefgh"

    # Top Labels
    y_top = (LABEL_MARGIN - LABEL_FONT_SIZE) // 2
    for i, ch in enumerate(files):
        sf = i if orient_white else 7 - i
        x = sf * SQUARE_SIZE + SQUARE_SIZE // 2
        surf = font.render(ch, True, pygame.Color("white"))
        w, h = surf.get_size()
        screen.blit(surf, (x - w // 2, y_top))

    # Bottom Labels
    y_bot = (
        TOP_MARGIN
        + BOARD_PIXELS
        + CAPTURE_HEIGHT
        + (LABEL_MARGIN - LABEL_FONT_SIZE) // 2
    )
    for i, ch in enumerate(files):
        sf = i if orient_white else 7 - i
        x = sf * SQUARE_SIZE + SQUARE_SIZE // 2
        surf = font.render(ch, True, pygame.Color("white"))
        w, h = surf.get_size()
        screen.blit(surf, (x - w // 2, y_bot))

    # Rank Labels
    for r in range(8):
        sr = 7 - r if orient_white else r
        lab = str(r + 1)
        surf = font.render(lab, True, pygame.Color("white"))
        w, h = surf.get_size()
        y = sr * SQUARE_SIZE + TOP_MARGIN + SQUARE_SIZE // 2 - h // 2

        # Left
        screen.blit(surf, (0, y))
        # Right
        screen.blit(surf, (WINDOW_WIDTH - w, y))


def draw_pieces(screen, board, images, dragging_src, orient_white):
    for sq, p in board.piece_map().items():
        if dragging_src is not None and sq == dragging_src:
            continue

        x, y = board_to_screen(sq, orient_white)
        key = ("w" if p.color else "b") + p.symbol().upper()
        screen.blit(images[key], (x, y))


def draw_move_hints(screen, board, src_sq, orient_white):
    for mv in board.legal_moves:
        if mv.from_square == src_sq:
            x, y = board_to_screen(mv.to_square, orient_white)
            cx = x + SQUARE_SIZE // 2
            cy = y + SQUARE_SIZE // 2
            pygame.draw.circle(
                screen, pygame.Color(108, 108, 68, 180), (cx, cy), DOT_RADIUS
            )


def draw_captured(screen, images, white_captures, black_captures):
    for i, p in enumerate(white_captures):
        prefix = "w" if p.color else "b"
        img = pygame.transform.smoothscale(
            images[prefix + p.symbol().upper()], (CAPTURE_HEIGHT, CAPTURE_HEIGHT)
        )

        x = i * CAPTURE_HEIGHT
        y = LABEL_MARGIN
        screen.blit(img, (x, y))

    base_y = TOP_MARGIN + BOARD_PIXELS
    for i, p in enumerate(black_captures):
        prefix = "w" if p.color else "b"
        img = pygame.transform.smoothscale(
            images[prefix + p.symbol().upper()], (CAPTURE_HEIGHT, CAPTURE_HEIGHT)
        )

        x = i * CAPTURE_HEIGHT
        screen.blit(img, (x, base_y))


def draw_engine_banner(screen, text):
    font = pygame.font.SysFont(None, ENGINE_FONT_SIZE)
    surf = font.render(text, True, pygame.Color("white"))

    bar = pygame.Surface((WINDOW_WIDTH, ENGINE_FONT_SIZE + 10), pygame.SRCALPHA)
    bar.fill((0, 0, 0, 150))

    screen.blit(bar, (0, WINDOW_HEIGHT - (ENGINE_FONT_SIZE + 10)))
    screen.blit(surf, (10, WINDOW_HEIGHT - (ENGINE_FONT_SIZE + 6)))


def choose_color(screen, clock):
    font = pygame.font.SysFont(None, ENGINE_FONT_SIZE)
    prompt = font.render("Choose your side", True, pygame.Color("white"))
    btn_font = pygame.font.SysFont(None, LABEL_FONT_SIZE)

    w_surf = btn_font.render("White", True, pygame.Color("black"))
    b_surf = btn_font.render("Black", True, pygame.Color("black"))

    btn_w, btn_h = w_surf.get_width() + 20, w_surf.get_height() + 10
    total_w = btn_w * 2 + 20
    start_x = (WINDOW_WIDTH - total_w) // 2

    y = WINDOW_HEIGHT // 2
    white_btn = pygame.Rect(start_x, y, btn_w, btn_h)
    black_btn = pygame.Rect(start_x + btn_w + 20, y, btn_w, btn_h)

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                exit()

            if ev.type == pygame.MOUSEBUTTONDOWN:
                if white_btn.collidepoint(ev.pos):
                    return chess.WHITE
                if black_btn.collidepoint(ev.pos):
                    return chess.BLACK

        screen.fill(pygame.Color("grey20"))
        screen.blit(prompt, ((WINDOW_WIDTH - prompt.get_width()) // 2, y - btn_h - 30))

        pygame.draw.rect(screen, pygame.Color("white"), white_btn)
        screen.blit(w_surf, (white_btn.x + 10, white_btn.y + 5))

        pygame.draw.rect(screen, pygame.Color("white"), black_btn)
        screen.blit(b_surf, (black_btn.x + 10, black_btn.y + 5))

        pygame.display.flip()
        clock.tick(FPS)


def show_end_game_dialog(screen, clock, message):
    title_font = pygame.font.SysFont(None, ENGINE_FONT_SIZE)
    btn_font = pygame.font.SysFont(None, LABEL_FONT_SIZE)

    title_surf = title_font.render(message, True, pygame.Color("white"))
    w_surf = btn_font.render("Restart", True, pygame.Color("black"))

    btn_w = w_surf.get_width() + 20
    btn_h = w_surf.get_height() + 10

    x = (WINDOW_WIDTH - btn_w) // 2
    y = (WINDOW_HEIGHT - btn_h) // 2 + 40

    restart_btn = pygame.Rect(x, y, btn_w, btn_h)

    quit_surf = btn_font.render("Quit", True, pygame.Color("black"))
    quit_btn = pygame.Rect(x, y + btn_h + 10, btn_w, btn_h)

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if restart_btn.collidepoint(ev.pos):
                    return "restart"

                if quit_btn.collidepoint(ev.pos):
                    pygame.quit()
                    sys.exit()

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        tx = (WINDOW_WIDTH - title_surf.get_width()) // 2
        ty = (WINDOW_HEIGHT - title_surf.get_height()) // 2 - 20
        screen.blit(title_surf, (tx, ty))

        pygame.draw.rect(screen, pygame.Color("white"), restart_btn)
        screen.blit(w_surf, (restart_btn.x + 10, restart_btn.y + 5))

        pygame.draw.rect(screen, pygame.Color("white"), quit_btn)
        screen.blit(quit_surf, (quit_btn.x + 10, quit_btn.y + 5))

        pygame.display.flip()
        clock.tick(FPS)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Chess Engine with Minimax")
    game_icon = pygame.image.load(asset_path("assets/chess_engine_icon.png"))
    pygame.display.set_icon(game_icon)

    clock = pygame.time.Clock()
    images = load_images()
    board = chess.Board()

    user_color = choose_color(screen, clock)
    orient_white = user_color == chess.WHITE
    cpu_color = not user_color

    white_captures, black_captures = [], []

    # Engine plays first if user chooses black
    if not orient_white:
        eng = get_minimax_move(board, cpu_color)
        board.push(eng)

    dragging = False
    drag_src_sq = None
    drag_img = None
    mouse_x = mouse_y = 0

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.MOUSEBUTTONDOWN and board.turn == user_color:
                sq = screen_to_board(ev.pos, orient_white)
                if sq is not None:
                    p = board.piece_at(sq)
                    if p and p.color == user_color:
                        dragging = True
                        drag_src_sq = sq
                        drag_img = images[
                            ("w" if p.color else "b") + p.symbol().upper()
                        ]
                        mouse_x, mouse_y = ev.pos
            elif ev.type == pygame.MOUSEMOTION and dragging:
                mouse_x, mouse_y = ev.pos
            elif ev.type == pygame.MOUSEBUTTONUP and dragging:
                dest = screen_to_board(ev.pos, orient_white)

                mv = None
                if dest is not None:
                    mv = chess.Move(drag_src_sq, dest)
                    if (
                        mv not in board.legal_moves
                        and board.piece_type_at(drag_src_sq) == chess.ROOK
                    ):
                        king_sq = board.king(user_color)

                        # Decide side by file comparison
                        if chess.square_file(drag_src_sq) > chess.square_file(king_sq):
                            # Kingside castle
                            mv = chess.Move(king_sq, king_sq + 2)
                        else:
                            # Queenside castle
                            mv = chess.Move(king_sq, king_sq - 2)

                if mv and board.is_capture(mv):
                    if board.is_en_passant(mv):
                        cap_sq = (
                            mv.to_square - 8
                            if board.turn == chess.WHITE
                            else mv.to_square + 8
                        )
                    else:
                        cap_sq = mv.to_square
                    cap = board.piece_at(cap_sq)
                    if cap:
                        (white_captures if cap.color else black_captures).append(cap)

                if mv and mv in board.legal_moves:
                    board.push(mv)
                    if board.is_checkmate():
                        winner = "White" if board.turn == chess.BLACK else "Black"
                        choice = show_end_game_dialog(
                            screen, clock, f"{winner} wins by checkmate"
                        )
                        if choice == "restart":
                            main()
                            return

                    # Redraw
                    screen.fill((50, 50, 50))
                    draw_board(screen)
                    draw_labels(screen, orient_white)
                    draw_pieces(screen, board, images, None, orient_white)

                    if orient_white:
                        draw_captured(screen, images, white_captures, black_captures)
                    else:
                        draw_captured(screen, images, black_captures, white_captures)

                    pygame.display.flip()

                    # Engine Thinking
                    draw_engine_banner(screen, "Engine thinking…")
                    pygame.display.flip()

                    # Engine Move
                    start = time.time()
                    eng = get_minimax_move(board, cpu_color)
                    if board.is_capture(eng):
                        if board.is_en_passant(eng):
                            cap_sq2 = (
                                eng.to_square - 8
                                if board.turn == chess.WHITE
                                else eng.to_square + 8
                            )
                        else:
                            cap_sq2 = eng.to_square

                        cap2 = board.piece_at(cap_sq2)

                        if cap2:
                            (white_captures if cap2.color else black_captures).append(
                                cap2
                            )
                    board.push(eng)
                    if board.is_checkmate():
                        winner = "White" if board.turn == chess.BLACK else "Black"
                        choice = show_end_game_dialog(
                            screen, clock, f"{winner} wins by checkmate"
                        )
                        if choice == "restart":
                            main()
                            return

                    print(f"Engine moved {eng} in {time.time()-start:.2f}s")

                dragging = False
                drag_src_sq = None
                drag_img = None

        screen.fill((50, 50, 50))
        draw_board(screen)
        draw_labels(screen, orient_white)
        draw_pieces(screen, board, images, drag_src_sq, orient_white)

        if orient_white:
            draw_captured(screen, images, white_captures, black_captures)
        else:
            draw_captured(screen, images, black_captures, white_captures)

        if dragging and drag_src_sq is not None:
            draw_move_hints(screen, board, drag_src_sq, orient_white)

        if dragging and drag_img:
            screen.blit(
                drag_img, (mouse_x - SQUARE_SIZE // 2, mouse_y - SQUARE_SIZE // 2)
            )
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
