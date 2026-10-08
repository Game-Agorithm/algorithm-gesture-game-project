from src.game_rules import KhlaSikoRules
class GameState:

    def __init__(self):
        self.board = KhlaSikoRules.get_initial_board()
        self.cows_to_place = KhlaSikoRules.INITIAL_COWS
        self.captured_cows = 0
        self.active_tigers = KhlaSikoRules.INITIAL_TIGERS

        self.current_turn = "C"
        self.phase = "PLACEMENT"
        self.winner = None
        self.selected_pos = None 
        self.hovered_pos = None

    def place_cow(self, row, col):
        if self.phase != "PLACEMENT" or self.current_turn != "C":
            return False

        if self.board[row][col] is None:
            self.board[row][col] = "C"
            self.cows_to_place -= 1

            if self.cows_to_place == 0:
                self.phase = "MOVEMENT"

            self.switch_turn()
            return True

        return False

    def move_piece(self, start_pos, end_pos):
        if self.phase != "MOVEMENT":
            return False

        start_r, start_c = start_pos
        end_r, end_c = end_pos

        if self.board[start_r][start_c] != self.current_turn:
            return False

        self.board[end_r][end_c] = self.board[start_r][start_c]
        self.board[start_r][start_c] = None

        self.switch_turn()
        return True

    def capture_cow(self, tiger_start, cow_pos, tiger_end):
        """Executes a tiger capture jump over a cow."""
        t_r, t_c = tiger_start
        c_r, c_c = cow_pos
        e_r, e_c = tiger_end

        if (
            self.board[t_r][t_c] == "T"
            and self.board[c_r][c_c] == "C"
            and self.board[e_r][e_c] is None
        ):

            self.board[e_r][e_c] = "T"
            self.board[t_r][t_c] = None
            self.board[c_r][c_c] = None
            self.captured_cows += 1

            self.switch_turn()
            return True

        return False

    def switch_turn(self):
        self.current_turn = "T" if self.current_turn == "C" else "C"

    def set_winner(self, winner_code):
        self.winner = winner_code
        self.phase = "GAME_OVER"