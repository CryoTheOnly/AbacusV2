import tkinter as tk
from tkinter import messagebox
import random
import copy
import json
import os

SAVE_FILE = "main/extra/games/sudoku/sudoku_save.json"

# ---------------- SUDOKU LOGIC ---------------- #

def valid(board, r, c, val):
    if any(board[r][j] == val for j in range(9)):
        return False
    if any(board[i][c] == val for i in range(9)):
        return False

    br, bc = 3 * (r // 3), 3 * (c // 3)
    for i in range(br, br + 3):
        for j in range(bc, bc + 3):
            if board[i][j] == val:
                return False
    return True

def find_empty(board):
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return r, c
    return None

def solve(board):
    empty = find_empty(board)
    if not empty:
        return True
    r, c = empty

    nums = list(range(1, 10))
    random.shuffle(nums)

    for val in nums:
        if valid(board, r, c, val):
            board[r][c] = val
            if solve(board):
                return True
            board[r][c] = 0
    return False

def generate_full_board():
    board = [[0]*9 for _ in range(9)]
    solve(board)
    return board

def generate_puzzle(difficulty):
    solution = generate_full_board()
    puzzle = copy.deepcopy(solution)

    if difficulty == "Easy":
        remove = 35
    elif difficulty == "Hard":
        remove = 55
    else:
        remove = 45

    while remove > 0:
        r = random.randint(0, 8)
        c = random.randint(0, 8)
        if puzzle[r][c] != 0:
            puzzle[r][c] = 0
            remove -= 1

    return puzzle, solution

# ---------------- GUI ---------------- #

class SudokuGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Sudoku Game")

        self.selected = None
        self.cells = []

        self.difficulty = tk.StringVar(value="Medium")
        tk.OptionMenu(root, self.difficulty, "Easy", "Medium", "Hard").pack()

        tk.Button(root, text="New Game", command=self.new_game).pack(pady=5)

        self.frame = tk.Frame(root)
        self.frame.pack()

        self.create_grid()

        # Try to load saved game
        if not self.load_game():
            self.new_game()

        root.bind("<Key>", self.key_pressed)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ----------- SAVE / LOAD -----------

    def save_game(self):
        data = {
            "puzzle": self.puzzle,
            "solution": self.solution,
            "difficulty": self.difficulty.get()
        }
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)

    def load_game(self):
        if not os.path.exists(SAVE_FILE):
            return False

        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)

            self.puzzle = data["puzzle"]
            self.solution = data["solution"]
            self.difficulty.set(data["difficulty"])

            self.update_display()
            return True
        except:
            return False

    def on_close(self):
        self.save_game()
        self.root.destroy()

    # ----------- UI -----------

    def get_box_color(self, r, c):
        box_row = r // 3
        box_col = c // 3
        return "#f0f0f0" if (box_row + box_col) % 2 == 0 else "#d9e6f2"

    def create_grid(self):
        for r in range(9):
            row = []
            for c in range(9):
                bg_color = self.get_box_color(r, c)

                label = tk.Label(
                    self.frame,
                    text="",
                    width=4,
                    height=2,
                    font=("Arial", 18),
                    borderwidth=1,
                    relief="solid",
                    bg=bg_color
                )

                label.grid(row=r, column=c)
                label.bind("<Button-1>",
                           lambda e, row=r, col=c: self.select_cell(row, col))

                row.append(label)
            self.cells.append(row)

    def new_game(self):
        self.puzzle, self.solution = generate_puzzle(self.difficulty.get())
        self.selected = None
        self.update_display()
        self.save_game()

    def update_display(self):
        for r in range(9):
            for c in range(9):
                val = self.puzzle[r][c]
                cell = self.cells[r][c]
                bg_color = self.get_box_color(r, c)

                if val != 0:
                    if val == self.solution[r][c]:
                        fg = "black"
                    else:
                        fg = "blue"
                    cell.config(text=str(val), fg=fg, bg=bg_color)
                else:
                    cell.config(text="", fg="blue", bg=bg_color)

    def select_cell(self, r, c):
        if self.puzzle[r][c] == 0:
            self.selected = (r, c)

            for row in range(9):
                for col in range(9):
                    self.cells[row][col].config(
                        bg=self.get_box_color(row, col)
                    )

            self.cells[r][c].config(bg="#a6d8ff")

    def key_pressed(self, event):
        if self.selected and event.char.isdigit():
            num = int(event.char)
            if 1 <= num <= 9:
                r, c = self.selected

                if self.solution[r][c] == num:
                    self.puzzle[r][c] = num
                    self.update_display()
                    self.save_game()
                    self.check_win()
                else:
                    messagebox.showinfo("Wrong", "Incorrect number!")

    def check_win(self):
        for r in range(9):
            for c in range(9):
                if self.puzzle[r][c] == 0:
                    return
        messagebox.showinfo("Victory!", "You solved the Sudoku!")

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    root = tk.Tk()
    app = SudokuGUI(root)
    root.mainloop()


