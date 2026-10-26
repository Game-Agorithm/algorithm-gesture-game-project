import random
from typing import Dict, List, Optional, Tuple

from src import config

Position = Tuple[int, int]
Board = List[List[Optional[str]]]

TIGER_PIECE = "T"
COW_PIECE = "C"


class KhlaSiKoRules:
    BOARD_SIZE = config.BOARD_SIZE
    INITIAL_COWS = config.INITIAL_COWS
    INITIAL_TIGERS = config.INITIAL_TIGERS
    CAPTURES_TO_WIN = config.CAPTURES_TO_WIN

    # ------------------------------------------------------------------
    # Board setup and geometry
    # ------------------------------------------------------------------

    @classmethod
    def get_initial_board(cls) -> Board:
        """Returns a 4x4 grid. 'T' = Tiger, 'C' = Cow, None = Empty."""
        board: Board = [
            [None for _ in range(cls.BOARD_SIZE)] for _ in range(cls.BOARD_SIZE)
        ]
        last = cls.BOARD_SIZE - 1
        corners = [(0, 0), (0, last), (last, 0), (last, last)]
        for row, col in corners[: cls.INITIAL_TIGERS]:
            board[row][col] = TIGER_PIECE
        return board

    @staticmethod
    def is_valid_position(r: int, c: int) -> bool:
        return 0 <= r < KhlaSiKoRules.BOARD_SIZE and 0 <= c < KhlaSiKoRules.BOARD_SIZE

    @classmethod
    def node_index(cls, row: int, col: int) -> int:
        """(row, col) -> node number 0..15."""
        return row * cls.BOARD_SIZE + col

    @classmethod
    def node_position(cls, index: int) -> Position:
        """Node number 0..15 -> (row, col)."""
        return divmod(index, cls.BOARD_SIZE)

    @staticmethod
    def get_orthogonal_neighbors(r, c):
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        neighbors = []
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if KhlaSiKoRules.is_valid_position(nr, nc):
                neighbors.append((nr, nc, dr, dc))
        return neighbors

    @classmethod
    def connections(cls) -> Dict[int, Tuple[int, ...]]:
        """Movement graph: node index -> indices of the nodes it is connected to."""
        graph = {}
        for index in range(cls.BOARD_SIZE ** 2):
            row, col = cls.node_position(index)
            graph[index] = tuple(
                cls.node_index(nr, nc)
                for nr, nc, _, _ in cls.get_orthogonal_neighbors(row, col)
            )
        return graph

    # ------------------------------------------------------------------
    # Looking at the board
    # ------------------------------------------------------------------

    @staticmethod
    def copy_board(board: Board) -> Board:
        return [row[:] for row in board]

    @classmethod
    def find_pieces(cls, board: Board, piece: Optional[str]) -> List[Position]:
        return [
            (r, c)
            for r in range(cls.BOARD_SIZE)
            for c in range(cls.BOARD_SIZE)
            if board[r][c] == piece
        ]

    @classmethod
    def empty_positions(cls, board: Board) -> List[Position]:
        return cls.find_pieces(board, None)

    # ------------------------------------------------------------------
    # Placing and moving
    # ------------------------------------------------------------------

    @classmethod
    def can_place_cow(cls, board, unplaced_cows, target_pos):
        r, c = target_pos
        if unplaced_cows <= 0:
            return False, "All cows have been placed."
        if not cls.is_valid_position(r, c):
            return False, "Position out of bounds."
        if board[r][c] is not None:
            return False, "Position is already occupied."
        return True, "Valid placement."

    @classmethod
    def get_valid_tiger_moves(cls, board, tiger_pos):
        """A tiger steps to an empty neighbour, or jumps over a neighbouring
        cow onto the empty node right behind it (that jump is a capture)."""
        r, c = tiger_pos
        if not cls.is_valid_position(r, c) or board[r][c] != 'T':
            return []
        valid_moves = []
        for nr, nc, dr, dc in cls.get_orthogonal_neighbors(r, c):
            if board[nr][nc] is None:
                valid_moves.append({'to': (nr, nc), 'is_capture': False, 'captured_pos': None})
            elif board[nr][nc] == 'C':
                land_r, land_c = nr + dr, nc + dc
                if cls.is_valid_position(land_r, land_c) and board[land_r][land_c] is None:
                    valid_moves.append({'to': (land_r, land_c), 'is_capture': True, 'captured_pos': (nr, nc)})
        return valid_moves

    @classmethod
    def get_valid_cow_moves(cls, board, unplaced_cows, cow_pos):
        """Cows only move after ALL cows are placed, one step to an empty neighbour."""
        if unplaced_cows > 0:
            return []

        r, c = cow_pos
        if not cls.is_valid_position(r, c) or board[r][c] != 'C':
            return []

        valid_moves = []
        for nr, nc, _, _ in cls.get_orthogonal_neighbors(r, c):
            if board[nr][nc] is None:
                valid_moves.append({'to': (nr, nc), 'is_capture': False, 'captured_pos': None})
        return valid_moves

    @classmethod
    def get_legal_moves(cls, board, unplaced_cows, position):
        """Legal moves for whichever piece stands on ``position``."""
        r, c = position
        if not cls.is_valid_position(r, c):
            return []
        piece = board[r][c]
        if piece == TIGER_PIECE:
            return cls.get_valid_tiger_moves(board, position)
        if piece == COW_PIECE:
            return cls.get_valid_cow_moves(board, unplaced_cows, position)
        return []

    @classmethod
    def is_valid_move(cls, board, unplaced_cows, start, end):
        return any(m['to'] == end for m in cls.get_legal_moves(board, unplaced_cows, start))

    @classmethod
    def all_moves(cls, board, unplaced_cows, piece):
        """Every legal move for one side as (start, move_dict) pairs."""
        moves = []
        for pos in cls.find_pieces(board, piece):
            for move in cls.get_legal_moves(board, unplaced_cows, pos):
                moves.append((pos, move))
        return moves

    @classmethod
    def side_has_moves(cls, board, unplaced_cows, piece):
        """True if ``piece`` ('T' or 'C') has something legal to do this turn."""
        if piece == COW_PIECE and unplaced_cows > 0:
            return bool(cls.empty_positions(board))     # can place a cow
        return bool(cls.all_moves(board, unplaced_cows, piece))

    @classmethod
    def can_tiger_capture(cls, board, tiger_pos=None):
        """True if the given tiger (or any tiger) has a capturing jump."""
        tigers = [tiger_pos] if tiger_pos else cls.find_pieces(board, TIGER_PIECE)
        return any(
            m['is_capture']
            for pos in tigers
            for m in cls.get_valid_tiger_moves(board, pos)
        )

    @classmethod
    def move_tiger(cls, board, start, end):
        """Move a tiger in place. Returns (ok, captured_position_or_None)."""
        move = next((m for m in cls.get_valid_tiger_moves(board, start) if m['to'] == end), None)
        if move is None:
            return False, None
        board[start[0]][start[1]] = None
        board[end[0]][end[1]] = TIGER_PIECE
        captured = move['captured_pos']
        if captured is not None:
            board[captured[0]][captured[1]] = None
        return True, captured

    @classmethod
    def move_cow(cls, board, unplaced_cows, start, end):
        """Move a cow in place (only legal once all cows are placed)."""
        if not cls.is_valid_move(board, unplaced_cows, start, end):
            return False
        board[start[0]][start[1]] = None
        board[end[0]][end[1]] = COW_PIECE
        return True

    @classmethod
    def capture_cow(cls, board, tiger_start, tiger_end):
        """Execute a tiger jump: remove the jumped cow, land the tiger.
        Returns the captured cow's position, or None if it was not a capture."""
        move = next(
            (m for m in cls.get_valid_tiger_moves(board, tiger_start)
             if m['to'] == tiger_end and m['is_capture']),
            None,
        )
        if move is None:
            return None
        cls.move_tiger(board, tiger_start, tiger_end)
        return move['captured_pos']

    # ------------------------------------------------------------------
    # Winning
    # ------------------------------------------------------------------
    @classmethod
    def check_tiger_win(cls, board, unplaced_cows, captured_cows):
        """Tigers win by capturing enough cows (or when no cows are left)."""
        if captured_cows >= cls.CAPTURES_TO_WIN:
            return True
        return unplaced_cows <= 0 and not cls.find_pieces(board, COW_PIECE)

    @classmethod
    def check_cow_win(cls, board, unplaced_cows):
        """Cows win once every cow is placed and no tiger can move or capture."""
        if unplaced_cows > 0:
            return False
        return not cls.all_moves(board, unplaced_cows, TIGER_PIECE)

    @classmethod
    def check_winner(cls, board, unplaced_cows, captured_cows):
        if cls.check_tiger_win(board, unplaced_cows, captured_cows):
            return "TIGERS"
        if cls.check_cow_win(board, unplaced_cows):
            return "COWS"
        return None

    @classmethod
    def check_game_over(cls, board, unplaced_cows, captured_cows):
        return cls.check_winner(board, unplaced_cows, captured_cows) is not None
# ----------------------------------------------------------------------
# Computer player
# ----------------------------------------------------------------------

class SimpleBot:
    """Very small rule-based opponent (no machine learning).

    Tiger bot:  1) take a capture if one exists (prefer one that allows
                   another capture next), 2) otherwise step to where it will
                   threaten the most cows and keep the most freedom,
                3) ties are broken randomly.
    Cow bot:    looks one move ahead and picks the placement / move that
                leaves the tigers the fewest captures, then the fewest moves
                (so it avoids obviously bad moves and tries to block).
    """

    def __init__(self, side: str, rng: Optional[random.Random] = None,
                 mistake_rate: float = 0.0):
        if side not in (TIGER_PIECE, COW_PIECE):
            raise ValueError("side must be 'T' or 'C'")
        self.side = side
        self.rng = rng or random.Random()
        # Chance (0..1) that the bot plays a random legal action instead of the
        # best one. Keeps the game beatable for a human playing the other side.
        self.mistake_rate = mistake_rate

    # -- public ---------------------------------------------------------

    def choose_action(self, board: Board, unplaced_cows: int):
        """Return {'type': 'place', 'position': pos} or
        {'type': 'move', 'start': pos, 'end': pos}, or None if no legal action."""
        if self.side == TIGER_PIECE:
            return self._choose_tiger(board, unplaced_cows)
        return self._choose_cow(board, unplaced_cows)

    # -- helpers --------------------------------------------------------

    @staticmethod
    def _tiger_options(board, unplaced_cows):
        """(number of capture jumps, number of tiger moves) on this board."""
        captures = mobility = 0
        for _, move in KhlaSiKoRules.all_moves(board, unplaced_cows, TIGER_PIECE):
            mobility += 1
            captures += 1 if move['is_capture'] else 0
        return captures, mobility

    def _pick_best(self, scored):
        if self.mistake_rate and self.rng.random() < self.mistake_rate:
            return self.rng.choice([action for _, action in scored])
        best = min(score for score, _ in scored)
        return self.rng.choice([action for score, action in scored if score == best])

    def _choose_tiger(self, board, unplaced_cows):
        moves = KhlaSiKoRules.all_moves(board, unplaced_cows, TIGER_PIECE)
        if not moves:
            return None
        scored = []
        for start, move in moves:
            after = KhlaSiKoRules.copy_board(board)
            KhlaSiKoRules.move_tiger(after, start, move['to'])
            next_captures, mobility = self._tiger_options(after, unplaced_cows)
            # lower score is better
            score = -(1000 if move['is_capture'] else 0) - 10 * next_captures - mobility
            scored.append((score, {'type': 'move', 'start': start, 'end': move['to']}))
        return self._pick_best(scored)

    def _choose_cow(self, board, unplaced_cows):
        scored = []
        if unplaced_cows > 0:
            for pos in KhlaSiKoRules.empty_positions(board):
                after = KhlaSiKoRules.copy_board(board)
                after[pos[0]][pos[1]] = COW_PIECE
                captures, mobility = self._tiger_options(after, unplaced_cows - 1)
                scored.append((100 * captures + mobility, {'type': 'place', 'position': pos}))
        else:
            for start, move in KhlaSiKoRules.all_moves(board, 0, COW_PIECE):
                after = KhlaSiKoRules.copy_board(board)
                KhlaSiKoRules.move_cow(after, 0, start, move['to'])
                captures, mobility = self._tiger_options(after, 0)
                scored.append((100 * captures + mobility, {'type': 'move', 'start': start, 'end': move['to']}))
        return self._pick_best(scored) if scored else None
