import unittest

from src.game_state import GameState


class GameStateTests(unittest.TestCase):
    def test_cow_placement_validates_position_and_turn(self):
        state = GameState()

        self.assertFalse(state.place_cow(-1, 0))
        self.assertFalse(state.place_cow(0, 0))
        self.assertEqual(state.cows_to_place, 12)
        self.assertTrue(state.place_cow(1, 1))
        self.assertEqual(state.board[1][1], "C")
        self.assertEqual(state.current_turn, "T")

    def test_piece_cannot_move_to_an_illegal_square(self):
        state = GameState()
        state.phase = "MOVEMENT"
        state.cows_to_place = 0
        state.board[1][0] = "C"

        self.assertFalse(state.move_piece((1, 0), (2, 2)))
        self.assertFalse(state.move_piece((1, 0), (0, 0)))
        self.assertEqual(state.board[1][0], "C")

    def test_tiger_capture_removes_cow_and_updates_turn(self):
        state = GameState()
        state.phase = "MOVEMENT"
        state.cows_to_place = 0
        state.current_turn = "T"
        state.board[0][1] = "C"

        self.assertTrue(state.capture_cow((0, 0), (0, 1), (0, 2)))
        self.assertEqual(state.board[0][0], None)
        self.assertEqual(state.board[0][1], None)
        self.assertEqual(state.board[0][2], "T")
        self.assertEqual(state.captured_cows, 1)
        self.assertEqual(state.current_turn, "C")


if __name__ == "__main__":
    unittest.main()
