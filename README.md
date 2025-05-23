# chess-engine

Minimax chess engine built with Python and Pygame.

## Move Ordering -

Pruning only happens when it gets good alpha or beta bounds early in the loop over moves.

If it examines “strong” moves first, it will raise alpha or or lower beta more quickly and prune more of the weaker moves that follow.
By sorting with Most Valuable Victim–Least Valuable Aggressor before recursing, it increases the likelihood of early pruning.

Sort captures by “most valuable victim, least valuable attacker”

Captures sorted by (value_of_captured - value_of_attacker), non-captures last

## Evaluation Function -

Terminal States

Piece Material Values and Piece Square Table Values

Currently in Check

Piece Mobility

King Safety

Shielded Pawns

Bishop Pairs

Rook Positioning on Open Files

Pawn Structure

## Minimax Algorithm -

Starting from the current position, imagine all possible moves, then all responses, and so on, building a tree of positions.
We recursively call the function and evaluate once we have reached the max depth
Choose highest or lowest the evaluation value: max or min nodes

## Alpha-Beta Pruning -

alpha: the best (highest) score that the maximizing side has found so far.

Beta: the best (lowest) score that the minimizing side has found so far.

At max node, try maximizing the score. For each recursive calll, find the highest alpha

At min node, try minimizing the score. For each recursive calll, find the lowest beta

If beta <= alpha, we know the opponent will avoid this branch, so we can cut off the rest of the children without exploring them.

## Transposition Table -

A transposition table is a dictionary that stores the result of a previous alpha-beta search from the same position as (depth_remaining, value, flag).

When the same position is revisisted in a different move order, we can use the transposition table

Look up the stored entry if it is in the table

If it was an exact score, it can be returned immediately.

If it was at the lower bound or uppder bound we return it if it was greater than beta or less than alpha
