"""Unit tests for the rules engine, turn handling and the bot (no Pygame/camera)."""

import random

import pytest

from src import config
from src.game_rules import Board, KhlaSiKoRules as Rules, SimpleBot
from src.game_state import GameState


def empty_board() -> Board:
    return [[None] * 4 for _ in range(4)]


def movement_state(tigers=(), cows=(), turn="T"):
    """A GameState in the MOVEMENT phase with exactly the given pieces."""
    state = GameState()
    state.board = empty_board()
    for r, c in tigers:
        state.board[r][c] = "T"
    for r, c in cows:
        state.board[r][c] = "C"
    state.phase, state.cows_to_place, state.current_turn = "MOVEMENT", 0, turn
    return state


# ---------------------------------------------------------------- board

def test_initial_board():
    board = Rules.get_initial_board()
    assert len(board) == 4 and all(len(row) == 4 for row in board)
    assert Rules.find_pieces(board, "T") == [(0, 0), (0, 3), (3, 0), (3, 3)]
    assert Rules.find_pieces(board, "C") == []
    assert len(Rules.empty_positions(board)) == 12


def test_node_indices_cover_0_to_15():
    assert Rules.node_index(0, 0) == 0 and Rules.node_index(3, 3) == 15
    for index in range(16):
        assert Rules.node_index(*Rules.node_position(index)) == index


def test_connections_are_orthogonal_and_symmetric():
    graph = Rules.connections()
    assert graph[0] == (4, 1) or set(graph[0]) == {1, 4}
    assert len(graph[5]) == 4 and len(graph[0]) == 2 and len(graph[1]) == 3
    for node, neighbours in graph.items():
        for other in neighbours:
            assert node in graph[other]


# ---------------------------------------------------------------- tiger

def test_legal_tiger_move():
    board = empty_board()
    board[1][1] = "T"
    moves = Rules.get_valid_tiger_moves(board, (1, 1))
    assert {m["to"] for m in moves} == {(0, 1), (2, 1), (1, 0), (1, 2)}
    assert not any(m["is_capture"] for m in moves)
    assert Rules.is_valid_move(board, 0, (1, 1), (1, 2))


def test_illegal_tiger_move():
    board = empty_board()
    board[1][1] = "T"
    assert not Rules.is_valid_move(board, 0, (1, 1), (2, 2))     # diagonal
    assert not Rules.is_valid_move(board, 0, (1, 1), (3, 1))     # too far
    assert Rules.get_valid_tiger_moves(board, (0, 0)) == []      # no tiger there


def test_tiger_capture_and_cow_removal():
    board = empty_board()
    board[0][0], board[0][1] = "T", "C"
    assert Rules.can_tiger_capture(board)
    assert Rules.capture_cow(board, (0, 0), (0, 2)) == (0, 1)
    assert board[0][0] is None and board[0][1] is None and board[0][2] == "T"


def test_tiger_cannot_jump_over_a_blocked_landing():
    board = empty_board()
    board[0][0], board[0][1], board[0][2] = "T", "C", "C"
    assert not Rules.can_tiger_capture(board)
    assert Rules.capture_cow(board, (0, 0), (0, 2)) is None
    board = empty_board()
    board[0][0], board[0][1], board[0][2] = "T", "C", "T"          # landing occupied
    assert not Rules.can_tiger_capture(board, (0, 0))


def test_move_tiger_reports_capture():
    board = empty_board()
    board[2][2], board[2][1] = "T", "C"
    assert Rules.move_tiger(board, (2, 2), (2, 0)) == (True, (2, 1))
    assert Rules.move_tiger(board, (2, 0), (3, 3)) == (False, None)


# ----------------------------------------------------------------- cows

def test_cows_cannot_move_during_placement():
    board = empty_board()
    board[1][1] = "C"
    assert Rules.get_valid_cow_moves(board, 5, (1, 1)) == []


def test_legal_cow_move():
    board = empty_board()
    board[1][1] = "C"
    moves = Rules.get_valid_cow_moves(board, 0, (1, 1))
    assert {m["to"] for m in moves} == {(0, 1), (2, 1), (1, 0), (1, 2)}
    assert Rules.move_cow(board, 0, (1, 1), (1, 2)) and board[1][2] == "C"


def test_illegal_cow_move():
    board = empty_board()
    board[1][1], board[1][2] = "C", "T"
    assert not Rules.is_valid_move(board, 0, (1, 1), (1, 2))     # occupied
    assert not Rules.is_valid_move(board, 0, (1, 1), (3, 3))     # far away
    assert not Rules.move_cow(board, 0, (1, 1), (2, 2))          # diagonal
    assert not Rules.can_place_cow(board, 3, (1, 2))[0]
    assert not Rules.can_place_cow(board, 0, (3, 3))[0]
    assert Rules.can_place_cow(board, 3, (3, 3))[0]


# -------------------------------------------------------------- winning

def test_tiger_wins_after_enough_captures():
    board = Rules.get_initial_board()
    assert Rules.check_winner(board, 3, config.CAPTURES_TO_WIN) == "TIGERS"
    assert Rules.check_tiger_win(board, 3, config.CAPTURES_TO_WIN)
    assert not Rules.check_tiger_win(board, 3, config.CAPTURES_TO_WIN - 1)


def test_tiger_wins_when_no_cows_are_left():
    board = Rules.get_initial_board()
    assert Rules.check_tiger_win(board, 0, 0)        # all placed, none on board


def test_cow_win_when_every_tiger_is_blocked():
    board = empty_board()
    board[0][0], board[0][1], board[1][0] = "T", "C", "C"
    board[0][2], board[2][0] = "C", "C"              # landings blocked
    assert Rules.check_cow_win(board, 0)
    assert Rules.check_winner(board, 0, 0) == "COWS"
    assert Rules.check_game_over(board, 0, 0)


def test_cows_cannot_win_before_all_are_placed():
    board = empty_board()
    board[0][0], board[0][1], board[1][0] = "T", "C", "C"
    board[0][2], board[2][0] = "C", "C"
    assert not Rules.check_cow_win(board, 2)


def test_game_not_over_at_start():
    assert Rules.check_winner(Rules.get_initial_board(), 12, 0) is None
    assert not Rules.check_game_over(Rules.get_initial_board(), 12, 0)


# ----------------------------------------------- state: turns / game over

def test_turn_switching():
    state = GameState()
    assert state.current_turn == "C" and state.turn_label == "COW TURN"
    assert state.place_cow(1, 1)
    assert state.current_turn == "T" and state.turn_label == "TIGER TURN"
    assert state.move_piece((0, 0), (0, 1))
    assert state.current_turn == "C"


def test_wrong_side_cannot_act():
    state = GameState()
    assert not state.move_piece((0, 0), (0, 1))          # tiger tries on cow's turn
    state.place_cow(1, 1)
    assert not state.place_cow(2, 2)                     # cow tries on tiger's turn


def test_game_over_blocks_further_moves():
    state = movement_state(tigers=[(0, 0)], cows=[(0, 1), (1, 0), (0, 2), (2, 0), (3, 3)], turn="C")
    assert state.move_piece((3, 3), (3, 2))              # cows move, tiger is now blocked
    assert state.winner == "COWS" and state.game_over and state.phase == "GAME_OVER"
    assert not state.move_piece((0, 0), (1, 1))


def test_capture_event_and_tiger_win():
    state = movement_state(tigers=[(0, 0)], cows=[(0, 1), (3, 3)])
    state.captured_cows = config.CAPTURES_TO_WIN - 1
    assert state.move_piece((0, 0), (0, 2))
    assert state.winner == "TIGERS"
    kinds = [e["type"] for e in state.pop_events()]
    assert kinds == ["capture", "win"]


def test_blocked_side_passes_instead_of_freezing():
    """Regression: with no legal cow move the old game froze forever."""
    state = movement_state(tigers=[(0, 0), (0, 3)], cows=[(3, 0)], turn="T")
    # block the single cow completely with tigers/edges, then let a tiger move
    state.board = empty_board()
    for r, c in [(0, 0), (3, 1), (2, 0)]:
        state.board[r][c] = "T"
    state.board[3][0] = "C"
    state.current_turn = "T"
    assert state.move_piece((0, 0), (0, 1))
    assert state.winner is None
    assert state.current_turn == "T"                     # cows passed
    assert any(e["type"] == "pass" for e in state.pop_events())


def test_nobody_can_move_means_cows_win():
    """A completely full board: neither side can act, so the tigers are boxed in."""
    state = movement_state(turn="C")
    for r in range(4):
        for c in range(4):
            state.board[r][c] = (
                "T" if (r, c) in [(0, 0), (0, 3), (3, 0), (3, 3)] else "C"
            )
    state._pass_if_blocked()
    assert state.winner == "COWS"


def test_modes_and_sides():
    one = GameState("single_player", "tiger")
    assert one.player_piece == "T" and one.bot_piece == "C"
    assert not one.is_human_turn                         # cows (the bot) start
    two = GameState("two_player")
    assert two.player_piece is None and two.bot_piece is None and two.is_human_turn
    assert GameState("single_player", "cow").is_human_turn


# ------------------------------------------------------------------ bot

def test_tiger_bot_takes_a_capture_when_available():
    board = empty_board()
    board[0][0], board[0][1], board[3][3] = "T", "C", "T"
    bot = SimpleBot("T", random.Random(1))
    for _ in range(20):
        action = bot.choose_action(board, 0)
        assert action is not None
        assert action["type"] == "move"
        assert (action["start"], action["end"]) == ((0, 0), (0, 2))


def test_cow_bot_avoids_an_obviously_bad_placement():
    board = empty_board()
    board[0][0], board[3][3] = "T", "T"
    bot = SimpleBot("C", random.Random(2))
    for _ in range(20):
        action = bot.choose_action(board, 5)
        assert action is not None
        assert action["type"] == "place"
        row, col = action["position"]
        test = [r[:] for r in board]
        test[row][col] = "C"
        assert not Rules.can_tiger_capture(test), "bot placed a cow where it can be captured"


def test_bots_only_play_legal_actions_and_games_finish():
    rng = random.Random(7)
    for _ in range(30):
        state = GameState()
        bots = {"C": SimpleBot("C", rng, 0.3), "T": SimpleBot("T", rng, 0.2)}
        for _ in range(400):
            if state.winner:
                break
            action = bots[state.current_turn].choose_action(state.board, state.cows_to_place)
            assert action is not None
            ok = (state.place_cow(*action["position"]) if action["type"] == "place"
                  else state.move_piece(action["start"], action["end"]))
            assert ok, f"bot made an illegal action: {action}"


def test_bot_with_no_moves_returns_none():
    board = empty_board()
    board[0][0], board[0][1], board[1][0], board[0][2], board[2][0] = "T", "C", "C", "C", "C"
    assert SimpleBot("T").choose_action(board, 0) is None


def test_bot_rejects_bad_side():
    with pytest.raises(ValueError):
        SimpleBot("X")
