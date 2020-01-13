import json
import pygame
import numpy as np
import time
pygame.init()

class ChunkGrabber():

    def __init__(self, how_many=100, seed=42):
        self.all_possible_rect_configs = self.get_all_possible_rect_configs()
        with open('smba_binary_chunks.json', 'r') as json_f:
            binary_chunks = np.array(json.load(json_f))
        np.random.seed(seed)
        np.random.shuffle(binary_chunks)
        self.binary_chunks = binary_chunks[:how_many]

    @staticmethod
    def get_all_possible_rect_configs():
        grid_xs = np.arange(0, 640, 40)
        grid_ys = np.arange(0, 640, 40)
        all_possible_rect_configs = []
        for x in grid_xs:
            temp = []
            for y in grid_ys:
                temp.append([x, y, 39, 39])
            all_possible_rect_configs.append(temp)
        return all_possible_rect_configs

    @staticmethod
    def is_solid(entry): return entry == 1

    def get_rect_configs_from(self, binary_chunk):
        rect_configs = []
        for i, row in enumerate(binary_chunk):
            for j, entry in enumerate(row):
                if self.is_solid(entry):
                    rect_configs.append(self.all_possible_rect_configs[j][i])
        return rect_configs

    def get_agent_rect_config_from(self, binary_chunk):
        for col_i in range(16):  # loop through the columns
            solid_indices = np.where(binary_chunk[:,col_i])[0]
            if len(solid_indices) > 0:  # loop through the rows
                bottom_solid_index = solid_indices[-1]
                for row_i in range(16):
                    bottom_row_i = 15 - row_i  # start from the bottom instead of the top
                    if not self.is_solid(binary_chunk[bottom_row_i, col_i]) and (bottom_row_i < bottom_solid_index):
                        return self.all_possible_rect_configs[col_i][bottom_row_i]

    def iter_rect_configs_for_chunks_and_agents(self):
        for bc in self.binary_chunks:
            yield self.get_rect_configs_from(bc), self.get_agent_rect_config_from(bc)

chunk_grabber = ChunkGrabber()
chunks_agents_iterator = chunk_grabber.iter_rect_configs_for_chunks_and_agents()
rect_configs, agent_rect_config = next(chunks_agents_iterator)

def is_inside(agent_rect_config, rect_configs):
    agent_x, agent_y, agent_width, agent_height = agent_rect_config
    endpoints = [(agent_x, agent_y), (agent_x+agent_width, agent_y), (agent_x, agent_y+agent_height), (agent_x+agent_width, agent_y+agent_height)]
    inside = False
    for rect_config in rect_configs:
        x, y, dx, dy = rect_config
        for p in endpoints:
            if (x <= p[0] and p[0] <= x + dx) and (y <= p[1] and p[1] <= y + dy):
                inside = True
    return inside

# GAME PHYSICS AND PARAMETERS

win_width, win_height = 640, 640
width, height = 40, 40
scale = 40  # each mario tile corresponds to 40 pygame units

win = pygame.display.set_mode((win_width, win_height))

frames_per_sec = 100

v = 6.7 * scale / frames_per_sec

is_jump = False
jump_t = 0

secs = 0.9742
num_jumps = secs * frames_per_sec
jump_count = num_jumps / 2
stepsize = secs / num_jumps

x_offset = 4.707
y_offset = - 0.97
a = - 16.72
b = 173.7
c = - 446.2
def quadratic(t):
    return 30 * (a * (t + x_offset) ** 2 + b * (t + x_offset) + c - y_offset)

# GAME LOOP

running = True
k_left, k_right, k_jump = False, True, False
locations = [(0,)]
playability_tracker = []
chunk_testing = 1
start = time.time()

while running:
    pygame.time.delay(1000 // frames_per_sec)
    pygame.display.set_caption(f'Super Mario Bros Binary; Testing Chunk {chunk_testing}')

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()

    # DRAW EVERYTHING
    win.fill((0, 0, 0))
    for rect_config in rect_configs:
        pygame.draw.rect(win, (255, 255, 255), rect_config)
    pygame.draw.rect(win, (255, 0, 0), agent_rect_config)
    pygame.display.update()

    # JUMP EFFECT
    if not is_jump:
        if keys[pygame.K_UP] or k_jump:
            is_jump = True
            starting_height = agent_rect_config[1]
            k_jump = False
    else:
        k_jump = False  # necessary for whatever reason I don't understand
        new_rect_config = agent_rect_config.copy()
        new_rect_config[1] = starting_height - quadratic(jump_t)
        if jump_count >= - num_jumps / 2 - 100 and not is_inside(new_rect_config, rect_configs):
        # new_rect_config[1] + 40 > win_height:
            agent_rect_config = new_rect_config
            jump_count -= 1
            jump_t += stepsize
        else:
            is_jump = False
            jump_count = num_jumps / 2
            jump_t = 0

    # if keys[pygame.K_LEFT] or k_left:
    #     new_rect_config = agent_rect_config.copy()
    #     new_rect_config[0] -= v
    #     if (new_rect_config[0] > 0) and not is_inside(new_rect_config, rect_configs):
    #         agent_rect_config = new_rect_config
    #     k_left = False

    if keys[pygame.K_RIGHT] or k_right:
        new_rect_config = agent_rect_config.copy()
        new_rect_config[0] += v
        if (new_rect_config[0] + width < win_width) and not is_inside(new_rect_config, rect_configs):
            agent_rect_config = new_rect_config

    # GRAVITY EFFECT
    new_rect_config = agent_rect_config.copy()
    new_rect_config[1] += 20  # helps check if the agent is on the ground
    # these two conditions are true only when the agent is falling
    # whenever the agent is on the ground, this condition is not met
    if not is_jump and not is_inside(new_rect_config, rect_configs):
        is_jump = True
        jump_count = 0
        jump_t = 1.1   # ideally, this number should be 1.0 (extremum of the quadratic)
        starting_height = agent_rect_config[1]

    # ========== SIMPLE AGENT ==========

    # === JUMPING MECHANISM ===
    # MAY FAIL BECAUSE THE CEILING IS TOO LOW, BECAUSE EVEN FIRST STEP UPWARDS
    # WOULD MAKE THE AGENT "INSIDE" SOLID TILES

    # * THE STUCK SENSOR
    locations.append(agent_rect_config)
    last_x, current_x = locations[-2][0], locations[-1][0]
    if current_x - last_x < 0.01: k_jump = True  # IF THE AGENT HAS NOT MOVED FORWARD SINCE LAST STEP, JUMP!

    # * THE TRAP SENSOR (3 LINES OF CODE)
    new_rect_config = agent_rect_config.copy()
    new_rect_config[0] += 10  # 10 PIXELS DOWNWARD
    new_rect_config[1] += 10  # 10 PIXELS FORWARD
    if not is_jump and not is_inside(new_rect_config, rect_configs): k_jump = True  # IF THE AGENT IS NOT JUMPING AND IS APPROACHING A TRAP, JUMP!

    # ========= DETERMINE PLAYABILITY ========

    # === CONDITIONS FOR NOT PLAYABLE ===
    at_least_one_condition_is_met = False
    now = time.time()

    if agent_rect_config[1] > win_height or (now - start > 15):

        playability_tracker.append(0)
        at_least_one_condition_is_met = True

    elif agent_rect_config[0] > (640 - 40 - 10):

        playability_tracker.append(1)
        at_least_one_condition_is_met = True

    # === GAME RESET ====
    if at_least_one_condition_is_met:

        chunk_testing += 1

        frames_per_sec = 100

        v = 6.7 * scale / frames_per_sec

        is_jump = False
        jump_t = 0

        secs = 0.9742
        num_jumps = secs * frames_per_sec
        jump_count = num_jumps / 2
        stepsize = secs / num_jumps

        x_offset = 4.707
        y_offset = - 0.97
        a = - 16.72
        b = 173.7
        c = - 446.2
        def quadratic(t):
            return 30 * (a * (t + x_offset) ** 2 + b * (t + x_offset) + c - y_offset)

        running = True
        k_left, k_right, k_jump = False, True, False
        locations = [(0,)]

        try:
            rect_configs, agent_rect_config = next(chunks_agents_iterator)
            start = time.time()
        except StopIteration:
            running = False

print('=============================================')
print('Playability proportion:', round(np.sum(playability_tracker) / len(playability_tracker), 2))
print('=============================================')
pygame.quit()



















#
