# Copyright: Yash + Divyansh, OpenEnv Hackathon 2026

"""Word Guessing (Anagram) Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

from .models import WordGuessingAction, WordGuessingObservation, WordGuessingState


class WordGuessingEnv(
    EnvClient[WordGuessingAction, WordGuessingObservation, WordGuessingState]
):
    """
    Client for the Word Guessing Anagram Environment.

    Example:
        >>> with WordGuessingEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.scrambled_letters)
        ...     result = client.step(WordGuessingAction(word_guess="CARS"))
        ...     print(result.observation.message)
    """

    def _step_payload(self, action: WordGuessingAction) -> Dict:
        """Convert action to JSON payload."""
        return {
            "word_guess": action.word_guess,
            "use_bank_on": action.use_bank_on,
            "bank_decision": action.bank_decision,
            "recovery_guess": action.recovery_guess,
        }

    def _parse_result(self, payload: Dict) -> StepResult[WordGuessingObservation]:
        """Parse server response into StepResult."""
        obs_data = payload.get("observation", {})
        observation = WordGuessingObservation(
            scrambled_letters=obs_data.get("scrambled_letters", []),
            words_found=obs_data.get("words_found", []),
            words_remaining=obs_data.get("words_remaining", 0),
            current_level=obs_data.get("current_level", 1),
            attempts_left_for_word=obs_data.get("attempts_left_for_word", 2),
            banked_chances=obs_data.get("banked_chances", 0),
            failed_words=obs_data.get("failed_words", []),
            message=obs_data.get("message", ""),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> WordGuessingState:
        """Parse server response into State object."""
        state_data = payload.get("state", payload)
        return WordGuessingState(
            episode_id=state_data.get("episode_id"),
            step_count=state_data.get("step_count", 0),
            scrambled_letters=state_data.get("scrambled_letters", []),
            found_words=state_data.get("found_words", []),
            current_level=state_data.get("current_level", 1),
            guesses_this_level=state_data.get("guesses_this_level", 0),
            max_wrong_per_level=state_data.get("max_wrong_per_level", 0),
            bank_choice_pending=state_data.get("bank_choice_pending", False),
            banked_chances=state_data.get("banked_chances", 0),
            failed_words=state_data.get("failed_words", []),
            total_reward=state_data.get("total_reward", 0.0),
            max_level=state_data.get("max_level", 5),
            level_results=state_data.get("level_results", []),
            recovery_pending=state_data.get("recovery_pending"),
        )
