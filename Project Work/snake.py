import pygame
import random
import sys

pygame.init()

# ================= SETTINGS =================
WIDTH, HEIGHT = 800, 600
CELL = 20
FPS = 10

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Classic Snake")

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 35)

WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)

high_score = 0  # memory for highest score


# ================= GAME RESET FUNCTION =================
def reset_game():
    snake = [(100, 100), (80, 100), (60, 100)]
    direction = "RIGHT"
    change_to = direction
    food = generate_food(snake)
    score = 0
    paused = False
    game_over = False
    return snake, direction, change_to, food, score, paused, game_over


# ================= FOOD GENERATOR =================
def generate_food(snake):
    while True:
        food = (
            random.randrange(0, WIDTH // CELL) * CELL,
            random.randrange(0, HEIGHT // CELL) * CELL,
        )
        if food not in snake:
            return food


# ================= DRAW FUNCTIONS =================
def draw_snake(snake, direction):
    head = snake[0]
    pygame.draw.rect(screen, (255, 255, 25), pygame.Rect(head[0], head[1], CELL, CELL))

    eye_size = CELL // 6

    if direction == "UP":
        eye1 = (head[0] + CELL//4, head[1] + CELL//4)
        eye2 = (head[0] + 3*CELL//4, head[1] + CELL//4)

    elif direction == "DOWN":
        eye1 = (head[0] + CELL//4, head[1] + 3*CELL//4)
        eye2 = (head[0] + 3*CELL//4, head[1] + 3*CELL//4)

    elif direction == "LEFT":
        eye1 = (head[0] + CELL//4, head[1] + CELL//4)
        eye2 = (head[0] + CELL//4, head[1] + 3*CELL//4)

    elif direction == "RIGHT":
        eye1 = (head[0] + 3*CELL//4, head[1] + CELL//4)
        eye2 = (head[0] + 3*CELL//4, head[1] + 3*CELL//4)

    pygame.draw.circle(screen, WHITE, eye1, eye_size)
    pygame.draw.circle(screen, WHITE, eye2, eye_size)

    for block in snake[1:]:
        pygame.draw.rect(screen, GREEN, pygame.Rect(block[0], block[1], CELL, CELL))



def draw_food(food):
    pygame.draw.ellipse(screen, RED, pygame.Rect(food[0], food[1], CELL, CELL))


def draw_text(text, x, y, color=WHITE):
    img = font.render(text, True, color)
    screen.blit(img, (x, y))


# ================= MAIN LOOP =================
snake, direction, change_to, food, score, paused, game_over_flag = reset_game()

while True:
    screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:

            # Movement controls (Arrow keys + WASD)
            if (event.key == pygame.K_UP or event.key == pygame.K_w) and direction != "DOWN":
                change_to = "UP"

            elif (event.key == pygame.K_DOWN or event.key == pygame.K_s) and direction != "UP":
                change_to = "DOWN"

            elif (event.key == pygame.K_LEFT or event.key == pygame.K_a) and direction != "RIGHT":
                change_to = "LEFT"

            elif (event.key == pygame.K_RIGHT or event.key == pygame.K_d) and direction != "LEFT":
                change_to = "RIGHT"


            # Pause
            elif event.key == pygame.K_p:
                paused = not paused

            # Restart after game over
            elif event.key == pygame.K_r and game_over_flag:
                snake, direction, change_to, food, score, paused, game_over_flag = reset_game()

            # Quit after game over
            elif event.key == pygame.K_q and game_over_flag:
                pygame.quit()
                sys.exit()

    if not paused and not game_over_flag:

        direction = change_to

        head_x, head_y = snake[0]

        if direction == "UP":
            head_y -= CELL
        elif direction == "DOWN":
            head_y += CELL
        elif direction == "LEFT":
            head_x -= CELL
        elif direction == "RIGHT":
            head_x += CELL

        new_head = (head_x, head_y)
        snake.insert(0, new_head)

        # Food eaten
        if new_head == food:
            score += 1
            food = generate_food(snake)
        else:
            snake.pop()  # only remove tail if not eating

        # Boundary collision
        if (
            head_x < 0
            or head_x >= WIDTH
            or head_y < 0
            or head_y >= HEIGHT
        ):
            game_over_flag = True
            if score > high_score:
                high_score = score

        # Self collision
        if new_head in snake[1:]:
            game_over_flag = True
            if score > high_score:
                high_score = score

    # ================= DRAW =================
    draw_snake(snake,direction)
    draw_food(food)

    draw_text(f"Score: {score}", 10, 10)
    draw_text(f"High Score: {high_score}", 10, 40)

    if paused and not game_over_flag:
        draw_text("PAUSED (Press P to Resume)", WIDTH // 4, HEIGHT // 2)

    if game_over_flag:
        draw_text("GAME OVER", WIDTH // 3, HEIGHT // 3, RED)
        draw_text("Press R to Restart", WIDTH // 3 - 20, HEIGHT // 2)
        draw_text("Press Q to Quit", WIDTH // 3 - 20, HEIGHT // 2 + 40)

    pygame.display.update()
    clock.tick(FPS)
