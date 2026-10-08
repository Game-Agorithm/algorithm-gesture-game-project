"""Game state and validated turn transitions for Khla Si Ko."""

from src.game_rules import KhlaSiKoRules


class GameState:
    def __init__(self):
        self.board = KhlaSiKoRules.get_initial_board()
        self.cows_to_place = KhlaSiKoRules.INITIAL_COWS
        self.captured_cows = 0
        self.active_tigers = KhlaSiKoRules.INITIAL_TIGERS
        self.current_turn = "C"
        self.phase = "PLACEMENT"
        self.winner = None
        self.selected_pos = None
        self.hovered_pos = None

    def place_cow(self, row, col):
        if self.phase != "PLACEMENT" or self.current_turn != "C":
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

    def _finish_turn(self):
        self.switch_turn()
        self.update_winner()

    def switch_turn(self):
        if not self.winner:
            self.current_turn = "T" if self.current_turn == "C" else "C"

    def update_winner(self):
        winner = KhlaSiKoRules.check_winner(
            self.board, self.cows_to_place, self.captured_cows
        )
        if winner is not None:
            self.set_winner(winner)

    def set_winner(self, winner_code):
        self.winner = winner_code
        self.phase = "GAME_OVER"
