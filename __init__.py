# python3
import neovim
import os
import copy

# What is this? Should this have source code?
class BrainfuckState(object):
    def __init__(self):
        self.index = 0
        self.memory = [0] * 30000
        self.input = b''
        self.used = 0
        self.output = b''
        self.code = ''
        self.ip = 0
        self.call_stack = ['bottom'] # this variable is for convenience
        self.fuel = 0

    @property
    def current(self):
        return self.memory[self.index]
    @current.setter
    def current(self, value):
        self.memory[self.index] = value % 256

    def run(self, s, fuel):
        self.fuel += fuel
        self.code += s
        while self.fuel and self.ip < len(self.code):
            c = self.code[self.ip]
            if self.call_stack[-1] == 'skip':
                if c == '[':
                    self.call_stack.append('skip')
                elif c == ']':
                    self.call_stack.pop()
            else:
                if c == '>':
                    self.index += 1
                elif c == '<':
                    self.index -= 1
                elif c == '+':
                    self.current = self.current + 1
                elif c == '-':
                    self.current = self.current - 1
                elif c == ',':
                    if self.used < len(self.input):
                        self.current = self.input[self.used]
                    else:
                        self.current = -1
                    self.used += 1
                elif c == '.':
                    self.output += bytes([self.current])
                elif c == '[':
                    if self.current:
                        self.call_stack.append(self.ip)
                    else:
                        self.call_stack.append('skip')
                elif c == ']':
                    if self.call_stack[-1] == 'skip':
                        self.call_stack.pop()
                    else:
                        if self.current:
                            self.ip = self.call_stack[-1]
                        else:
                            self.call_stack.pop()
            self.ip += 1
            self.fuel -= 1

@neovim.plugin
class BrainfuckDebugger(object):
    def __init__(self, vim):
        self.vim = vim

    def get_the_window(self, name):
        def find():
            return list(filter(lambda window: os.path.basename(window.buffer.name) == name, self.vim.windows))
        windows = find()
        if windows:
            return windows[0]
        else:
            current_window = self.vim.current.window
            self.vim.command(':3split')
            self.vim.command(':edit {}'.format(name.replace('*','\\*')))
            self.vim.command(':setlocal buftype=nofile')
            self.vim.command(':setlocal noswapfile')
            it = self.vim.current.window
            self.vim.current.window = current_window
            return it

    def get_input_window(self):
        return self.get_the_window('*brainfuck-input*')
    def get_memory_window(self):
        return self.get_the_window('*brainfuck-memory*')
    def get_output_window(self):
        return self.get_the_window('*brainfuck-output*')

    def format_input(self):
        newlines = { 'dos': '\r\n', 'unix': '\n', 'max' : '\r' }
        fileformat = self.vim.eval('&fileformat')
        lines = self.get_input_window().buffer[:]
        return newlines[fileformat].join(lines).encode()

    def format_memory(self):
        width = 16
        n = len(self.brainfuck.memory)
        while n and not self.brainfuck.memory[n-1]:
            n -= 1
        n = max(n, self.brainfuck.index+1)
        lines = []
        for y in range(0,n,width):
            memory = self.brainfuck.memory[y:y+width]
            line = []
            for x, value in enumerate(memory):
                s = str(value)
                if y * width + x == self.brainfuck.index:
                    s = '*' + s
                line.append(s.rjust(3))
            lines.append(' '.join(line))
        return lines

    @neovim.command('Evl', range='', nargs='*', sync=True)
    def eval(self, args, rng):
        try:
            s = repr(eval(self.vim.current.line))
        except Exception as e:
            s = repr(e)
        self.vim.current.buffer.append(s)

    @neovim.command('BFRun', range='', nargs='*', sync=True)
    def run(self, args, rng):
        self.brainfuck = BrainfuckState()
        self.brainfuck.input += self.format_input()
        try:
            h, w = self.vim.current.window.cursor
            for y in range(h):
                s = self.vim.current.buffer[y]
                if y == h-1:
                    s = s[:w+1]
                self.brainfuck.run(s, 10000)
        except Exception as e:
            self.vim.err_write(str(e))
        if self.brainfuck.fuel == 0:
            self.vim.err_write('Interrupted')
        current_window = self.vim.current.window
        self.vim.current.window = self.get_output_window()
        self.vim.command(':%d')
        self.vim.command(':put ={}'.format(repr(self.brainfuck.output)[1:]))
        self.vim.command(':1d')
        self.vim.current.window = current_window
        self.vim.current.window = self.get_memory_window()
        self.vim.current.buffer[:] = self.format_memory()
        self.vim.current.window = current_window

    @neovim.autocmd('InsertLeave', pattern='*.bf', sync=True)
    def on_insert_leave(self):
        self.vim.command(':BFRun')

    @neovim.autocmd('CursorMoved', pattern='*.bf', sync=True)
    def on_insert_leave(self):
        self.vim.command(':BFRun')
