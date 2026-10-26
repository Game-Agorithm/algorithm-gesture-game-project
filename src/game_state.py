"""Game state and validated turn transitions for Khla Si Ko."""

from typing import Optional

from src import config
from src.game_rules import KhlaSiKoRules


class GameState:
    def __init__(
        self,
        game_mode: str = config.MODE_SINGLE,
        player_side: str = config.COW,
        round_number: int = 1,
        game_style: str = config.DEFAULT_GAME_STYLE,
    ):
        self.game_mode = game_mode              # "single_player" | "two_player"
        self.player_side = player_side          # side the human plays in single player
        self.round_number = round_number
        self.game_style = game_style

        self.board = KhlaSiKoRules.get_initial_board()
        self.cows_to_place = KhlaSiKoRules.INITIAL_COWS
        self.captured_cows = 0
        self.active_tigers = KhlaSiKoRules.INITIAL_TIGERS
        self.current_turn = "C"                 # cows place first
        self.phase = "PLACEMENT"                # PLACEMENT -> MOVEMENT -> GAME_OVER
        self.winner = None                      # None | "TIGERS" | "COWS"
        self.selected_pos = None
        self.hovered_pos = None

        # What just happened (place / move / capture / pass / win). The app
        # reads these with pop_events() to play sounds and animations.
        self.last_event = None
        self.event_id = 0
        self.events = []

    # ------------------------------------------------------------------
    # Read-only helpers
    # ------------------------------------------------------------------

    @property
    def game_over(self) -> bool:
        return self.winner is not None

    @property
    def tiger_positions(self):
        return KhlaSiKoRules.find_pieces(self.board, "T")

    @property
    def cow_positions(self):
        return KhlaSiKoRules.find_pieces(self.board, "C")

    @property
    def cows_remaining(self) -> int:
        """Cows still alive: waiting to be placed + standing on the board."""
        return self.cows_to_place + len(self.cow_positions)

    @property
    def turn_label(self) -> str:
        return "COW TURN" if self.current_turn == "C" else "TIGER TURN"

    @property
    def player_piece(self) -> Optional[str]:
        """'T' / 'C' for the human in single player, None in two player."""
        if self.game_mode != config.MODE_SINGLE:
            return None
        return "T" if self.player_side == config.TIGER else "C"

    @property
    def bot_piece(self) -> Optional[str]:
        piece = self.player_piece
        return None if piece is None else ("C" if piece == "T" else "T")

    @property
    def is_human_turn(self) -> bool:
        return not self.winner and self.current_turn != self.bot_piece

    def _emit(self, kind: str, **data):
        self.event_id += 1
        self.last_event = {"type": kind, **data}
        self.events.append(self.last_event)

    def pop_events(self):
        """Return and clear the events that happened since the last call."""
        events, self.events = self.events, []
        return events

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def place_cow(self, row, col):
        if self.winner or self.phase != "PLACEMENT" or self.current_turn != "C":
            return False

        valid, _ = KhlaSiKoRules.can_place_cow(
            self.board, self.cows_to_place, (row, col)
        )
        if not valid:
            return False

        self.board[row][col] = "C"
        self.cows_to_place -= 1
        if self.cows_to_place == 0:
            self.phase = "MOVEMENT"

        self._emit("place", piece="C", to=(row, col))
        self._finish_turn()
        return True

    def get_valid_moves(self, position):
        row, col = position
        if not KhlaSiKoRules.is_valid_position(row, col):
            return []
        piece = self.board[row][col]
        if piece != self.current_turn:
            return []

        if piece == "T":
            return KhlaSiKoRules.get_valid_tiger_moves(self.board, position)
        if piece == "C" and self.phase == "MOVEMENT":
            return KhlaSiKoRules.get_valid_cow_moves(
                self.board, self.cows_to_place, position
            )
        return []

    def move_piece(self, start_pos, end_pos):
        if self.winner or self.phase == "GAME_OVER":
            return False

        start_row, start_col = start_pos
        end_row, end_col = end_pos
        if not (
            KhlaSiKoRules.is_valid_position(start_row, start_col)
            and KhlaSiKoRules.is_valid_position(end_row, end_col)
        ):
            return False

        legal_move = next(
            (
                move
                for move in self.get_valid_moves(start_pos)
                if move["to"] == end_pos
            ),
            None,
        )
        if legal_move is None:
            return False

        piece = self.board[start_row][start_col]
        self.board[start_row][start_col] = None
        self.board[end_row][end_col] = piece
        captured_pos = legal_move["captured_pos"]
        if captured_pos is not None:
            captured_row, captured_col = captured_pos
            self.board[captured_row][captured_col] = None
            self.captured_cows += 1

        self._emit(
            "capture" if captured_pos is not None else "move",
            piece=piece, start=start_pos, to=end_pos, captured=captured_pos,
        )
        self._finish_turn()
        return True

    def capture_cow(self, tiger_start, cow_pos, tiger_end):
        """Execute a legal tiger jump over the specified cow."""
        if self.current_turn != "T":
            return False
        move = next(
            (
                item
                for item in self.get_valid_moves(tiger_start)
                if item["to"] == tiger_end and item["captured_pos"] == cow_pos
            ),
            None,
        )
        if move is None:
            return False
        return self.move_piece(tiger_start, tiger_end)

    # ------------------------------------------------------------------
    # Turn handling
    # ------------------------------------------------------------------

    def _finish_turn(self):
        self.selected_pos = None
        self.switch_turn()
        self.update_winner()
        self._pass_if_blocked()

    def switch_turn(self):
        if not self.winner:
            self.current_turn = "T" if self.current_turn == "C" else "C"

    def _pass_if_blocked(self):
        """If the side to move has no legal action, the turn passes to the
        other side (otherwise the game would freeze)."""
        if self.winner:
            return
        side = self.current_turn
        if KhlaSiKoRules.side_has_moves(self.board, self.cows_to_place, side):
            return
        other = "T" if side == "C" else "C"
        if not KhlaSiKoRules.side_has_moves(self.board, self.cows_to_place, other):
            # Nobody can move: the tigers are boxed in, so the cows win.
            self.set_winner("COWS")
            return
        self.current_turn = other
        self._emit("pass", side=side)

    def update_winner(self):
        winner = KhlaSiKoRules.check_winner(
            self.board, self.cows_to_place, self.captured_cows
        )
        if winner is not None:
            self.set_winner(winner)

    def set_winner(self, winner_code):
        self.winner = winner_code
        self.phase = "GAME_OVER"
        self.selected_pos = None
        self._emit("win", winner=winner_code)
