class KhlaSiKoRules:
    BOARD_SIZE = 4
    INITIAL_COWS = 12
    INITIAL_TIGERS = 4

    @staticmethod
    def get_initial_board():
        """Returns a 4x4 grid. 'T' = Tiger, 'C' = Cow, None = Empty."""
        board = [[None for _ in range(KhlaSiKoRules.BOARD_SIZE)] for _ in range(KhlaSiKoRules.BOARD_SIZE)]
        board[0][0] = 'T'
        board[0][3] = 'T'
        board[3][0] = 'T'
        board[3][3] = 'T'
        return board

    @staticmethod
    def is_valid_position(r, c):
        return 0 <= r < KhlaSiKoRules.BOARD_SIZE and 0 <= c < KhlaSiKoRules.BOARD_SIZE

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
    def check_winner(cls, board, unplaced_cows, captured_cows):
        if captured_cows >= 4:
            return "TIGERS"
        if unplaced_cows > 0:
            return None

        for r in range(cls.BOARD_SIZE):
            for c in range(cls.BOARD_SIZE):
                if board[r][c] == 'T' and cls.get_valid_tiger_moves(board, (r, c)):
                    return None

        return "COWS"