#!/usr/bin/env python3
"""
utils.py - Utilidades compartidas para scripts de análisis TFT

Contiene funciones de conversión y helpers usados por múltiples scripts.
"""


def round_to_stage(round_num: int) -> str:
    """
    Convierte un número de ronda absoluto al formato de stage legible.

    La conversión es:
    - Rondas 1-3: Stage 1 (1-1, 1-2, 1-3)
    - Rondas 4-7: Stage 2 (2-1, 2-2, 2-3, 2-4)
    - Rondas 8-11: Stage 3 (3-1, 3-2, 3-3, 3-4)
    - Rondas 12-15: Stage 4 (4-1, 4-2, 4-3, 4-4)
    - Rondas 16-19: Stage 5 (5-1, 5-2, 5-3, 5-4)
    - Rondas 20-23: Stage 6 (6-1, 6-2, 6-3, 6-4)
    - Rondas 24-27: Stage 7 (7-1, 7-2, 7-3, 7-4)
    - Rondas 28+: Stage 8+

    Args:
        round_num: Número de ronda absoluto (1-based)

    Returns:
        String en formato "X-Y" donde X es el stage y Y es la ronda dentro del stage

    Examples:
        >>> round_to_stage(1)
        '1-1'
        >>> round_to_stage(8)
        '3-1'
        >>> round_to_stage(35)
        '9-4'
    """
    if round_num <= 0:
        return "0-0"

    # Stage 1 tiene 3 rondas (1, 2, 3)
    if round_num <= 3:
        return f"1-{round_num}"

    # Stages 2+ tienen 4 rondas cada uno
    # Ronda 4 = Stage 2-1, Ronda 5 = Stage 2-2, etc.
    adjusted = round_num - 4  # Ajustar para que ronda 4 sea índice 0
    stage = (adjusted // 4) + 2  # Stage 2 empieza en ronda 4
    round_in_stage = (adjusted % 4) + 1

    return f"{stage}-{round_in_stage}"


def stage_to_round(stage_str: str) -> int:
    """
    Convierte un formato de stage "X-Y" a número de ronda absoluto.

    Args:
        stage_str: String en formato "X-Y"

    Returns:
        Número de ronda absoluto

    Examples:
        >>> stage_to_round('1-1')
        1
        >>> stage_to_round('3-1')
        8
    """
    try:
        parts = stage_str.split("-")
        stage = int(parts[0])
        round_in_stage = int(parts[1])

        if stage == 1:
            return round_in_stage

        # Stages 2+ tienen 4 rondas
        return 3 + (stage - 2) * 4 + round_in_stage

    except (ValueError, IndexError):
        return 0


if __name__ == "__main__":
    # Test de la función
    print("Test de round_to_stage:")
    test_rounds = [1, 2, 3, 4, 5, 8, 12, 16, 20, 24, 28, 35, 40]
    for r in test_rounds:
        stage = round_to_stage(r)
        back = stage_to_round(stage)
        print(f"  Ronda {r:2d} -> Stage {stage} -> Ronda {back:2d}")
