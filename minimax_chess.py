import chess
import random
import os
import time
import math

PIECE_SQUARE_TABLES = {
    chess.PAWN: [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [50, 50, 50, 50, 50, 50, 50, 50],
        [10, 10, 20, 30, 30, 20, 10, 10],
        [5, 5, 10, 25, 25, 10, 5, 5],
        [0, 0, 0, 20, 20, 0, 0, 0],
        [5, -5, -10, 0, 0, -10, -5, 5],
        [5, 10, 10, -20, -20, 10, 10, 5],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    chess.KNIGHT: [
        [-50, -40, -30, -30, -30, -30, -40, -50],
        [-40, -20, 0, 5, 5, 0, -20, -40],
        [-30, 5, 10, 15, 15, 10, 5, -30],
        [-30, 0, 15, 20, 20, 15, 0, -30],
        [-30, 5, 15, 20, 20, 15, 5, -30],
        [-30, 0, 10, 15, 15, 10, 0, -30],
        [-40, -20, 0, 0, 0, 0, -20, -40],
        [-50, -40, -30, -30, -30, -30, -40, -50],
    ],
    chess.BISHOP: [
        [-20, -10, -10, -10, -10, -10, -10, -20],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-10, 0, 5, 10, 10, 5, 0, -10],
        [-10, 5, 5, 10, 10, 5, 5, -10],
        [-10, 0, 10, 10, 10, 10, 0, -10],
        [-10, 10, 10, 10, 10, 10, 10, -10],
        [-10, 5, 0, 0, 0, 0, 5, -10],
        [-20, -10, -10, -10, -10, -10, -10, -20],
    ],
    chess.ROOK: [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [5, 10, 10, 10, 10, 10, 10, 5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [0, 0, 0, 5, 5, 0, 0, 0],
    ],
    chess.QUEEN: [
        [-20, -10, -10, -5, -5, -10, -10, -20],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-10, 0, 5, 5, 5, 5, 0, -10],
        [-5, 0, 5, 5, 5, 5, 0, -5],
        [0, 0, 5, 5, 5, 5, 0, -5],
        [-10, 5, 5, 5, 5, 5, 0, -10],
        [-10, 0, 5, 0, 0, 0, 0, -10],
        [-20, -10, -10, -5, -5, -10, -10, -20],
    ],
    chess.KING: [
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-20, -30, -30, -40, -40, -30, -30, -20],
        [-10, -20, -20, -20, -20, -20, -20, -10],
        [20, 20, 0, 0, 0, 0, 20, 20],
        [20, 30, 10, 0, 0, 10, 30, 20],
    ],
}

# Constants for the evaluation function
CHECK_BONUS = 50  # reward for giving a check
CHECK_PENALTY = 50  # penalty for receiving a check
MOBILITY_WEIGHT = 5  # per‐move bonus
KING_SHIELD_WEIGHT = 10  # reward per pawn in front of the king
KING_ATTACK_PENALTY = 20  # penalty per enemy attack on the king
BISHOP_PAIR_BONUS = 50  # Bonus for both bishops
ROOK_OPEN_FILE_BONUS = 25  # Bonus for rook on a file with no pawns blocking it
DOUBLED_PAWN_PENALTY = 25  # Penalty for doubled pawn
ISOLATED_PAWN_PENALTY = 20  # Penalty for isolated pawn
PASSED_PAWN_BONUS = 30  # Bonus for pawns with no enemy pawns ahead on adjacent files

piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 350,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}
max_depth = 4
recursion_count = 0

EXACT, LOWERBOUND, UPPERBOUND = 0, 1, 2
transposition_table = {}  # (depth_left, value, flag)


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def get_user_move(board):
    user_input = input("Enter your move...")
    user_move = chess.Move.from_uci(user_input)

    while user_move not in board.legal_moves:
        user_input = input("Enter a valid move...")
        user_move = chess.Move.from_uci(user_input)

    return user_move


def get_random_move(board):
    random_move = random.choice(list(board.legal_moves))
    return random_move


# Move ordering
def order_moves(board):
    # Pruning only happens when it gets good alpha or beta bounds early in the loop over moves.
    # If it examines “strong” moves first, it will raise alpha or or lower beta more quickly and prune more of the weaker moves that follow.
    # By sorting with Most Valuable Victim–Least Valuable Aggressor before recursing, it increases the likelihood of early pruning.

    moves = list(board.legal_moves)

    # Sort captures by “most valuable victim, least valuable attacker”
    # Captures sorted by (value_of_captured - value_of_attacker), non-captures last
    def move_score(move):
        if board.is_capture(move):
            victim = board.piece_type_at(move.to_square) or 0
            attacker = board.piece_type_at(move.from_square) or 0

            return piece_values.get(victim, 0) - piece_values.get(attacker, 0)
        return -1

    return sorted(moves, key=move_score, reverse=True)


def evaluate_board(board, target_color):
    # Terminal states
    if board.is_checkmate():
        return math.inf if board.turn != target_color else -math.inf

    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    # Piece Material Values and Piece Square Table Values
    for square, piece in board.piece_map().items():
        # Get value of all pieces on the board
        piece_val = piece_values[piece.piece_type]
        if piece.color == target_color:
            score += piece_val
        else:
            score -= piece_val

        # Squares of Pieces
        piece_table = PIECE_SQUARE_TABLES[piece.piece_type]
        piece_x, piece_y = square % 8, square // 8

        # If the piece is Black, mirror the table
        table_val = (
            piece_table[7 - piece_y][piece_x]
            if piece.color == chess.BLACK
            else piece_table[piece_y][piece_x]
        )
        if piece.color == target_color:
            score += table_val
        else:
            score -= table_val

    # Is in Check
    if board.is_check():
        if board.turn != target_color:
            score += CHECK_BONUS
        else:
            score -= CHECK_PENALTY

    # Piece Mobility
    temp_turn = board.turn
    board.turn = target_color

    own_num_legal_moves = len(list(board.legal_moves))
    board.turn = not target_color
    opp_num_legal_moves = len(list(board.legal_moves))
    score += MOBILITY_WEIGHT * (own_num_legal_moves - opp_num_legal_moves)

    board.turn = temp_turn

    # King safety
    king_square = board.king(target_color)

    # Shield pawns directly ahead (and diagonally ahead)
    f, r = chess.square_file(king_square), chess.square_rank(king_square)
    directions = (
        [(-1, 1), (0, 1), (1, 1)]
        if target_color == chess.WHITE
        else [(-1, -1), (0, -1), (1, -1)]
    )
    shield = 0
    for df, dr in directions:
        nf, nr = f + df, r + dr
        if 0 <= nf < 8 and 0 <= nr < 8:
            p = board.piece_type_at(chess.square(nf, nr))
            if p == chess.PAWN and board.color_at(chess.square(nf, nr)) == target_color:
                shield += 1
    score += KING_SHIELD_WEIGHT * shield

    # Penalty for attackers on king square
    attackers = board.attackers(not target_color, king_square)
    score -= KING_ATTACK_PENALTY * len(attackers)

    # Bishop pair
    if len(board.pieces(chess.BISHOP, target_color)) >= 2:
        score += BISHOP_PAIR_BONUS
    if len(board.pieces(chess.BISHOP, not target_color)) >= 2:
        score -= BISHOP_PAIR_BONUS

    # Rook on an open file
    for rook_sq in board.pieces(chess.ROOK, target_color):
        file = chess.square_file(rook_sq)
        # if no friendly pawns on that file → open
        if not any(
            board.piece_type_at(chess.square(file, rr)) == chess.PAWN
            and board.color_at(chess.square(file, rr)) == target_color
            for rr in range(8)
        ):
            score += ROOK_OPEN_FILE_BONUS

    for rook_sq in board.pieces(chess.ROOK, not target_color):
        file = chess.square_file(rook_sq)
        if not any(
            board.piece_type_at(chess.square(file, rr)) == chess.PAWN
            and board.color_at(chess.square(file, rr)) == (not target_color)
            for rr in range(8)
        ):
            score -= ROOK_OPEN_FILE_BONUS

    # Pawn structure
    for color, sign in [(target_color, 1), (not target_color, -1)]:
        files = {f: 0 for f in range(8)}
        pawn_sqs = list(board.pieces(chess.PAWN, color))
        for sq in pawn_sqs:
            files[chess.square_file(sq)] += 1
        # Doubled pawns
        for f, count in files.items():
            if count > 1:
                score -= sign * DOUBLED_PAWN_PENALTY * (count - 1)

        # Isolated pawns
        for sq in pawn_sqs:
            f = chess.square_file(sq)
            if files.get(f - 1, 0) == 0 and files.get(f + 1, 0) == 0:
                score -= sign * ISOLATED_PAWN_PENALTY

    return score


# Minimax algorithm without alpha-beta pruning
def minimax(board, target_color, depth=0):
    # Starting from the current position, imagine all possible moves, then all responses, and so on, building a tree of positions.
    # We recursively call the function and evaluate once we have reached the max depth
    # Choose highest or lowest the evaluation value: max or min nodes

    global recursion_count
    recursion_count += 1

    if depth == max_depth:
        return evaluate_board(board, target_color)

    # Terminal states
    if board.is_checkmate():
        return evaluate_board(board, target_color)

    if board.is_stalemate():
        return evaluate_board(board, target_color)

    if board.is_insufficient_material():
        return evaluate_board(board, target_color)

    if target_color == board.turn:
        # Maximizing Step
        max_eval_val = -math.inf

        for move in board.legal_moves:
            board.push(move)

            move_eval = minimax(board, target_color, depth=depth + 1)
            max_eval_val = max(max_eval_val, move_eval)

            board.pop()

        return max_eval_val
    else:
        # Minimizing Step
        min_eval_val = math.inf

        for move in board.legal_moves:
            board.push(move)

            move_eval = minimax(board, target_color, depth=depth + 1)
            min_eval_val = min(min_eval_val, move_eval)

            board.pop()

        return min_eval_val


# Minimax algorithm with alpha-beta pruning and a transposition table
def minimax_alphabeta(board, target_color, alpha=-math.inf, beta=math.inf, depth=0):
    # Alpha-beta Pruning
    # alpha: the best (highest) score that the maximizing side has found so far.
    # Beta: the best (lowest) score that the minimizing side has found so far.

    # At max node, try maximizing the score. For each recursive calll, find the highest alpha
    # At min node, try minimizing the score. For each recursive calll, find the lowest beta
    # If beta <= alpha, we know the opponent will avoid this branch, so we can cut off the rest of the children without exploring them.

    # Transposition Table
    # A transposition table is  a dictionary that stores the result of a previous alpha-beta search from the same position as (depth_remaining, value, flag).
    # When the same position is revisisted in a different move order, we can use the transposition table

    # Look up the stored entry if it is in the table
    # If it was an exact score, it can be returned immediately.
    # If it was at the lower bound or uppder bound we return it if it was greater than beta or less than alpha

    global recursion_count, transposition_table
    recursion_count += 1

    key = board._transposition_key()
    depth_left = max_depth - depth

    alpha_original = alpha

    if key in transposition_table:
        saved_depth, saved_val, saved_flag = transposition_table[key]
        if saved_depth >= depth_left:
            if saved_flag == EXACT:
                return saved_val
            if saved_flag == LOWERBOUND and saved_val >= beta:
                return saved_val
            if saved_flag == UPPERBOUND and saved_val <= alpha:
                return saved_val

    # Max Depth reached or reached Terminal states
    if depth == max_depth or board.is_game_over():
        val = evaluate_board(board, target_color)
        transposition_table[key] = (depth_left, val, EXACT)
        return val

    if target_color == board.turn:
        # Maximizing Step
        best = -math.inf

        for move in order_moves(board):
            board.push(move)
            score = minimax_alphabeta(board, target_color, alpha, beta, depth=depth + 1)
            board.pop()

            best = max(best, score)

            # Alpha
            alpha = max(alpha, score)
            if beta <= alpha:
                break
    else:
        # Minimizing Step
        best = math.inf

        for move in order_moves(board):
            board.push(move)
            score = minimax_alphabeta(board, target_color, alpha, beta, depth=depth + 1)
            board.pop()

            best = min(best, score)

            # Beta
            beta = min(beta, score)
            if beta <= alpha:
                break

    if best <= alpha_original:
        flag = UPPERBOUND
    elif best >= beta:
        flag = LOWERBOUND
    else:
        flag = EXACT

    transposition_table[key] = (depth_left, best, flag)
    return best


def get_minimax_move(board, target_color):
    global recursion_count, transposition_table
    transposition_table = {}
    recursion_count = 0

    start_time = time.time()
    # Maximizing for target_color player
    best_move = None
    best_eval = -math.inf

    for move in order_moves(board):
        board.push(move)
        current_eval = minimax_alphabeta(
            board, target_color, alpha=-math.inf, beta=math.inf, depth=1
        )
        if current_eval > best_eval:
            best_eval = current_eval
            best_move = move

        board.pop()

    end_time = time.time()
    print(f"Minimax took {(end_time - start_time):.2f}s to move")

    return best_move


if __name__ == "__main__":
    gameOver = False
    board = chess.Board()

    playerChoice = input("Choose black or white (B or W)")
    while playerChoice not in ["B", "W", "b", "w"]:
        playerChoice = input("Choose black or white (B or W)")

    if playerChoice in ["B", "b"]:
        userColor = chess.BLACK
        cpuColor = chess.WHITE
    else:
        userColor = chess.WHITE
        cpuColor = chess.BLACK

    while not gameOver:
        clear_console()
        print(board.unicode(borders=True, invert_color=True))

        if board.turn == userColor:
            move = get_user_move(board)
        else:
            move = get_minimax_move(board, cpuColor)
            print(f"Recursion count: {recursion_count}")

        print(f"{'WHITE' if board.turn else 'BLACK'} played: {move}")

        board.push(move)

        # time.sleep(1)
        gameOver = board.is_game_over()
