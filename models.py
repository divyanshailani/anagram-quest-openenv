# Copyright: Yash + Divyansh, OpenEnv Hackathon 2026

"""
Data models for the Anagram Word Guessing Environment.

Combined design: 5 levels, multiple anagrams per level, banking system,
auto-progression, and 2-mode actions (guess or use bank).
"""

from typing import List, Optional

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


class WordGuessingAction(Action):
    """Three modes: guess a word, spend a banked chance, or make a bank decision."""

    word_guess: Optional[str] = Field(
        default=None,
        description="The agent's anagram word guess (must use all scrambled letters)",
    )
    use_bank_on: Optional[str] = Field(
        default=None,
        description="Start recovery challenge: spend 1 banked chance on this level number",
    )
    bank_decision: Optional[str] = Field(
        default=None,
        description="Bank choice: 'preserve' (save to bank), 'current' (add +2 guesses to current level)",
    )
    recovery_guess: Optional[str] = Field(
        default=None,
        description="Guess for recovery challenge — the word you think was missed",
    )


class WordGuessingObservation(Observation):
    """What the agent sees after every reset() or step()."""

    scrambled_letters: List[str] = Field(default_factory=list, description="The scrambled letters to form words from")
    words_found: List[str] = Field(default_factory=list, description="Words found in current level")
    words_remaining: int = Field(default=0, description="Words left to find in current level")
    current_level: int = Field(default=1, description="Current level (1-5)")
    attempts_left_for_word: int = Field(default=2, description="Guesses remaining for current word target")
    banked_chances: int = Field(default=0, description="Saved chances from 1st-try correct guesses (available from level 3)")
    failed_words: List[str] = Field(default_factory=list, description="Words the agent failed and can retry with banked chances")
    message: str = Field(default="", description="Feedback message to the agent")


class WordGuessingState(State):
    """Internal state — tracks full game across all 5 levels.

    NOTE: valid_anagrams is NOT stored here to prevent leaking answers
    via the public /state endpoint. See Codex Patch 2.
    """

    scrambled_letters: List[str] = Field(default_factory=list)
    found_words: List[str] = Field(default_factory=list, description="Words found in CURRENT level")
    current_level: int = Field(default=1)
    guesses_this_level: int = Field(default=0, description="Total guesses so far this level")
    max_wrong_per_level: int = Field(default=0, description="Max wrong guesses before level auto-ends (computed: 2 × total_words)")
    bank_choice_pending: bool = Field(default=False, description="True when player must choose what to do with a bank chance")
    banked_chances: int = Field(default=0)
    failed_words: List[dict] = Field(default_factory=list, description="Failed words with level origin: [{word, level}]")
    total_reward: float = Field(default=0.0)
    max_level: int = Field(default=5)
    level_results: List[dict] = Field(default_factory=list, description="Per-level results: [{level, found, failed, letters}]")
    recovery_pending: Optional[dict] = Field(default=None, description="Active recovery challenge: {level, letters, word, sorted_key}")
