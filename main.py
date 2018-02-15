import json
import random
import time
import os

try:
    clear = lambda: os.system('clear')
except:
    clear = lambda: os.system('cls')


class QTable(object):

    def __init__(self, game, unit, alpha=0.95, gamma=0.95, eps=0.95):
        """
        :state: key: (pos_x, pos_y, mark)
        :game: reference to game object
        :unit: reference to unit object
        :alpha: coefficient
        :gamma: coefficient
        :eps: error of random
        """
        self.game = game
        self.unit = unit
        self.alpha = alpha
        self.gamma = gamma
        self.eps = eps
        self.state = dict()

    @staticmethod
    def from_json(game, unit, body):
        q_table = QTable(game, unit)
        q_table.alpha = body['alpha']
        q_table.gamma = body['gamma']
        q_table.eps = body['eps']

        """Couldn't dump tuple key other way"""
        state = body['state']
        for k, v in state.items():
            key = json.loads(k)
            for i in range(len(key)):
                if key[i] == -10:
                    key[i] = Unit.X
                elif key[i] == -20:
                    key[i] = Unit.O
            q_table.state[tuple(key)] = v

        return q_table

    def json(self):
        state = dict()
        for k, v in self.state.items():
            key = list(k)
            for i in range(len(key)):
                if key[i] == Unit.X:
                    key[i] = -10
                elif key[i] == Unit.O:
                    key[i] = -20
            state[repr(key)] = v
        obj = {
            'alpha': self.alpha,
            'gamma': self.gamma,
            'eps': self.eps,
            'state': state
        }
        return obj

    def run_model(self, reward=-1):
        if self.unit.prev_state not in self.state:
            self.state[self.unit.prev_state] = 0

        nvec = []
        for i in self.game.get_actions():
            cstate = self.unit.state + i + tuple(self.unit.mark)
            if cstate not in self.state:
                self.state[cstate] = 0
            nvec.append(self.state[cstate])
        if nvec:
            nvec = max(nvec)
            self.state[self.unit.prev_state] = (
                self.state[self.unit.prev_state] + self.alpha * (
                    reward - self.state[self.unit.prev_state]
                    + self.gamma * nvec))

    def get_next_move(self):
        if random.random() < self.eps:
            act = random.choice(self.game.get_actions())
        else:
            best = [(0, 0), float('-inf')]
            for i in self.game.get_actions():
                next_state = self.unit.state + i + tuple(self.unit.mark)
                if next_state not in self.state:
                    self.state[next_state] = 0
                if best[1] < self.state[next_state]:
                    best = [i, self.state[next_state]]
            act = best[0]
        return act


class Unit(object):

    PLAYER = 0
    BOT = 1

    O = 'O'
    X = 'X'

    def __init__(self, game, unit_type=BOT, mark=X, name='Player', alpha=0.95, gamma=0.95, eps=0.95):
        """
        :game: reference to game object
        :unit_type: Bot or player
        :mark: mark to display on board
        :name: name to display
        """
        self.name = name
        self.q_table = QTable(game=game, unit=self, alpha=alpha, gamma=gamma, eps=eps)
        self.game = game
        self.unit_type = unit_type
        self.mark = mark
        self.stats = {'wins': 0, 'loses': 0, 'draws': 0}
        self.state = (0, 0, mark)
        self.prev_state = (0, 0, mark)

    @staticmethod
    def from_json(game, body):
        if body['unit_type'] == Unit.PLAYER:
            u_class = Player
        else:
            u_class = Bot
        unit = u_class(game, body['unit_type'], body['mark'], body['name'])
        unit.q_table = QTable.from_json(game, unit, body['q_table'])
        unit.stats = body['stats']
        unit.state = tuple(body['state'])
        unit.prev_state = tuple(body['prev_state'])
        return unit

    def json(self):
        return {
            'name': self.name,
            'q_table': self.q_table.json(),
            'unit_type': self.unit_type,
            'mark': self.mark,
            'stats': self.stats,
            'state': self.state,
            'prev_state': self.prev_state
        }

    def __str__(self):
        return self.name

    def move(self):
        print('Func move: Not implemented')

    def restart(self):
        self.state = (0, 0, self.mark)
        self.prev_state = (0, 0, self.mark)


class Player(Unit):

    def move(self):
        print('Enter coordinates: ')
        try:
            x, y = list(map(int, input().split()))
            if not self.game.check_position(x, y, message=True):
                self.move()
            else:
                self.prev_state = self.state
                self.state += (x, y, self.mark)
                self.game.desk[x][y] = self.mark
        except Exception as e:
            print('Invalid format! {}'.format(e))
            self.move()


class Bot(Unit):

    def move(self, rand=False):
        if self.game.sleep:
            time.sleep(1)
        if rand:
            x, y = random.randint(0, self.game.size-1), random.randint(0, self.game.size-1)
        else:
            x, y = self.q_table.get_next_move()
        print('Bot coordinates: {} {}'.format(x, y))
        if not self.game.check_position(x, y):
            self.move()
        else:
            self.game.desk[x][y] = self.mark
        return (x, y, self.mark)


class Game(object):

    EMPTY = '.'

    WIN = 100
    LOSE = -100
    DRAW = 10
    NONE = -1

    SERIALIZE_EVERY = 100

    def serialize(self):
        with open(self.filename, 'w') as f:
            body = self.json()
            f.write(json.dumps(body))
            print('Serialization SUCCESS')

    def deserialize(self, unit1=True, unit2=True):
        try:
            with open(self.filename, 'r') as f:
                body = json.loads(f.read())
                if unit1:
                    self.unit1 = Unit.from_json(self, body['unit1'])
                if unit2:
                    self.unit2 = Unit.from_json(self, body['unit2'])
                self.iteration = body['iteration']
                self.size = body['size']
                self.desk = body['desk']
                self.iterations = body['iterations']
                self.turn = Unit.from_json(self, body['turn'])
                print('Deserialization success')
        except Exception as e:
            print('Deserialization ERROR', str(e))

    def json(self):
        obj = {
            'unit1': self.unit1.json(),
            'unit2': self.unit2.json(),
            'iteration': self.iteration,
            'size': self.size,
            'desk': self.desk,
            'iterations': self.iterations,
            'turn': self.turn.json()
        }
        return obj

    def __init__(self, filename, size=3, iterations=30000, sleep=True):
        """
        :filename: serialization file
        :size: size of table
        :iterations: Number of iterations to stop
        :sleep: Turn slow mode when True
        """
        self.sleep = sleep
        self.filename = filename
        self.iteration = 0
        self.size = size
        self.init_table()
        self.iterations = iterations

    def init_users(self, unit1, unit2):
        self.unit1 = unit1
        self.unit2 = unit2
        self.turn = unit1

    def get_actions(self):
        result = list()
        for i in range(self.size):
            for j in range(self.size):
                if self.desk[i][j] == self.EMPTY:
                    result.append((i, j))
        return result

    def start(self):
        """
        """
        while True:
            self.draw()
            self.move()
            self.iteration += 1
            if self.iteration == self.iterations:
                break
            if (self.SERIALIZE_EVERY + self.iteration) % self.SERIALIZE_EVERY == 0:
                self.serialize()
            print('Iteration:', self.iteration)

    def move(self, restart=True):
        """
        :status equals reward
        """
        new_state = self.turn.move()
        winner, status = self.check_winner()
        if self.turn.unit_type == Unit.BOT:
            self.turn.prev_state = self.turn.state
            self.unit1.state += new_state
            self.unit2.state += new_state
            self.turn.q_table.run_model(reward=status)
        finish = False
        if status == self.DRAW:
            finish = True
            print('Game Over! DRAW')
        elif winner:
            finish = True
            print('Game Over! Winner: {}'.format(winner))
        if finish and restart:
            if self.sleep:
                time.sleep(2)
            self.draw()
            self.add_stats(winner, status)
            print(self.unit1, self.unit1.stats)
            print(self.unit2, self.unit2.stats)
            self.restart()
        self.switch_turn()

    def add_stats(self, winner, status):
        if status == self.DRAW:
            self.unit1.stats['draws'] += 1
            self.unit2.stats['draws'] += 1
        elif self.unit1 == winner:
            self.unit1.stats['wins'] += 1
            self.unit2.stats['loses'] += 1
        else:
            self.unit2.stats['wins'] += 1
            self.unit1.stats['loses'] += 1

    def switch_turn(self):
        if self.turn == self.unit1:
            self.turn = self.unit2
        else:
            self.turn = self.unit1

    def init_table(self):
        self.desk = [['.' for j in range(self.size)] for i in range(self.size)]

    def restart(self):
        self.step = 0
        self.iteration += 1
        self.init_table()
        self.unit1.restart()
        self.unit2.restart()

    def check_winner(self):
        d1 = list()
        d2 = list()

        for i in range(self.size):
            d1.append(self.desk[i][i])
            d2.append(self.desk[i][self.size - i - 1])

        for i in [self.unit1, self.unit2]:
            for j in range(self.size):
                if self.desk[j].count(i.mark) == self.size:
                    return i, self.WIN
            for j in range(self.size):
                col = [self.desk[x][j] for x in range(self.size)]
                if col.count(i.mark) == self.size:
                    return i, self.WIN

            if d1.count(i.mark) == self.size or d2.count(i.mark) == self.size:
                return i, self.WIN

        non_empty = 0
        for i in range(self.size):
            for j in range(self.size):
                if self.desk[i][j] != self.EMPTY:
                    non_empty += 1
        if non_empty == self.size * self.size:
            return None, self.DRAW

        return None, self.NONE

    def draw(self):
        # clear()
        print()
        for i in range(self.size):
            for j in range(self.size):
                print(self.desk[i][j], end=' ')
            print()
        print()

    def check_position(self, x, y, message=False):
        try:
            if self.desk[x][y] != '.':
                if message:
                    print('Place is not empty!')
                return False
            return True
        except IndexError:
            print('Invalid coordinates. Valid range: N: {} M: {}'.format(
                self.size, self.size))


if __name__ == '__main__':
    game = Game(filename='first_game.json', sleep=True, iterations=1000)
    player = Player(game=game, unit_type=Unit.PLAYER, mark=Unit.X, name='Player')
    bot_aiba = Bot(game=game, unit_type=Unit.BOT, mark=Unit.O, name='Bot AIBA', alpha=0.95, gamma=0.95, eps=0.95)
    bot_meshok = Bot(game=game, unit_type=Unit.BOT, mark=Unit.X, name='Bot Meshok', alpha=1.2, gamma=0.8, eps=0.9)

    # Uncomment when playing bot VS bot    
    game.init_users(unit1=bot_meshok, unit2=bot_aiba)
    game.deserialize(unit1=False, unit2=True)

    # Uncomment when playing player VS bot
    # game.init_users(unit1=player, unit2=bot_aiba)
    # game.deserialize(unit1=False, unit2=True)

    game.start()
