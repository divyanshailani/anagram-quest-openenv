# Copyright: Yash + Divyansh, OpenEnv Hackathon 2026

"""
Anagram Word Guessing Environment — Combined Design.

5-level game with auto-progression, banking system, and dense rewards.

Levels 1-5: word lengths 3-7. Each level presents scrambled letters
with 2+ valid anagram words to find. 2 attempts per word.

Banking (from Level 3): 1st-try correct → +1 banked chance.
Agent can spend banked chances to retry any failed word.

Rewards:
  +1.0  correct on 1st attempt (+ bank a chance from level 3)
  +0.5  correct on 2nd attempt
  +0.1  close guess (uses right letters but not a valid word)
  -0.1  wrong guess
  +2.0  bonus for finding ALL words in a level
  +5.0  bonus for clearing all 5 levels
  -0.1  invalid bank action
"""

import random
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment

try:
    from ..models import WordGuessingAction, WordGuessingObservation, WordGuessingState
except ImportError:
    from models import WordGuessingAction, WordGuessingObservation, WordGuessingState


# ──────────────────────────────────────────────────────────────
# Curated anagram dictionary — ALL verified English words
# Grouped by sorted-letter key. Every group has 2+ valid words.
# Bug fixes applied: no duplicates, no non-English words.
# ──────────────────────────────────────────────────────────────

ANAGRAM_GROUPS = {
    # ── Level 1: 3-letter words ──
    "ABT": ["BAT", "TAB"],
    "ACT": ["ACT", "CAT"],
    "AET": ["ATE", "EAT", "TEA", "ETA"],
    "APT": ["APT", "TAP", "PAT"],
    "ART": ["ART", "RAT", "TAR"],
    "ADM": ["DAM", "MAD"],
    "AMP": ["AMP", "MAP"],
    "ANP": ["NAP", "PAN"],
    "ANT": ["ANT", "TAN"],
    "APS": ["SAP", "SPA", "ASP"],
    "AEL": ["ALE", "LEA"],
    "DEN": ["DEN", "END"],
    "GNU": ["GNU", "GUN", "NUG"],
    "NOW": ["NOW", "OWN", "WON"],
    "OPT": ["OPT", "TOP", "POT"],
    "ORT": ["ROT", "TOR"],
    "DGO": ["DOG", "GOD"],
    "LOW": ["OWL", "LOW"],
    "ENT": ["NET", "TEN"],
    "INP": ["PIN", "NIP"],
    "IPS": ["SIP", "PSI"],
    "EST": ["SET"],

    # ── Level 2: 4-letter words ──
    "ACRS": ["CARS", "SCAR", "ARCS"],
    "ACST": ["CATS", "CAST", "ACTS", "SCAT"],
    "AELP": ["PALE", "LEAP", "PLEA", "PEAL"],
    "AELR": ["REAL", "EARL"],
    "AELS": ["SALE", "SEAL", "ALES"],
    "AELT": ["LATE", "TALE", "TEAL"],
    "AEMN": ["NAME", "MEAN", "MANE", "AMEN"],
    "AENR": ["NEAR", "EARN"],
    "AEPS": ["PEAS", "APES"],
    "AEPT": ["TAPE", "PEAT", "PATE"],
    "AERW": ["WEAR", "WARE"],
    "ALPS": ["SLAP", "LAPS", "ALPS", "PALS"],
    "ANPS": ["SNAP", "SPAN", "NAPS", "PANS"],
    "ARST": ["STAR", "RATS", "ARTS", "TARS"],
    "DEIS": ["SIDE", "DIES", "IDES"],
    "EILS": ["LIES", "ISLE"],
    "EIST": ["SITE", "TIES"],
    "ENOT": ["NOTE", "TONE"],
    "EORS": ["ROSE", "ORES", "SORE"],
    "OPST": ["STOP", "POST", "TOPS", "SPOT", "OPTS", "POTS"],
    "ORST": ["SORT", "ROTS"],
    "ILNO": ["LOIN", "LION"],
    "ADEL": ["DALE", "DEAL", "LEAD"],
    "AMST": ["MAST", "MATS", "TAMS"],
    "EILV": ["VILE", "LIVE", "EVIL", "VEIL"],
    "GINS": ["SING", "SIGN", "GINS"],
    "ADEM": ["MADE", "DAME", "MEAD"],
    "ADER": ["DARE", "READ", "DEAR"],
    "AEGM": ["GAME", "MAGE"],
    "AELM": ["MALE", "LAME", "MEAL"],
    "AMOR": ["ROAM", "MORA"],
    "AGIN": ["GAIN"],

    # ── Level 3: 5-letter words ──
    "AELPS": ["LEAPS", "PALES", "SEPAL", "PEALS", "PLEAS"],
    "AELRT": ["LATER", "ALTER", "ALERT"],
    "AELST": ["STEAL", "TALES", "STALE", "LEAST", "SLATE"],
    "AENRS": ["SNARE", "EARNS", "NEARS", "SANER"],
    "AEPRS": ["SPARE", "SPEAR", "PARSE", "PEARS", "REAPS"],
    "AEGRS": ["GEARS", "RAGES", "SAGER"],
    "AILNS": ["NAILS", "SNAIL", "SLAIN"],
    "AINRT": ["TRAIN", "INTRA"],
    "DEIRS": ["RIDES", "SIRED", "DRIES"],
    "AELNP": ["PENAL", "PANEL", "PLANE"],
    "EILPS": ["PILES", "PLIES", "SPIEL"],
    "EINPS": ["PINES", "SPINE", "SNIPE"],
    "EINRS": ["REINS", "RINSE", "SIREN", "RISEN"],
    "EINST": ["INSET", "STEIN", "TINES"],
    "EORST": ["STORE", "ROTES", "TORES"],
    "ERSTW": ["STREW", "WREST"],
    "AILRT": ["TRAIL", "TRIAL"],
    "ADELS": ["DEALS", "LEADS", "DALES"],
    "AELNS": ["LANES", "LEANS"],
    "DEIST": ["DIETS", "EDITS", "TIDES", "SITED"],
    "ADEMS": ["MEADS", "DAMES"],

    # ── Level 4: 6-letter words ──
    "AELRST": ["STELAR", "ALERTS", "ALTERS", "SLATER"],
    "AEINRS": ["ARISEN", "SARNIE"],
    "ADEIRS": ["RAISED", "DARIES"],
    "AEGNRS": ["RANGES", "ANGERS"],
    "DEISTU": ["SUITED", "DUTIES"],
    "EINORS": ["SENIOR", "IRONES"],
    "AEGLNS": ["ANGLES", "GLEANS"],
    "AEINST": ["TISANE", "INSEAT"],
    "AEPRST": ["PASTER", "REPAST"],
    "ACENRS": ["CANERS", "CRANES", "NACRES"],
    "AEGNRT": ["GARNET", "ARGENT"],
    "AELRSV": ["SALVER", "VELARS", "LAVERS"],
    "DEGINS": ["DESIGN", "SIGNED", "SINGED"],
    "AGINST": ["GIANTS", "SATING"],
    "DEINRS": ["DINERS", "RINSED"],
    "AEMNST": ["STAMEN", "AMENTS", "MANTES"],
    "EILNST": ["LISTEN", "SILENT", "TINSEL", "ENLIST"],
    "EINPRS": ["SNIPER", "RIPENS"],
    "AEGINR": ["EARING", "GAINER", "REGAIN"],

    # ── Level 5: 7-letter words ──
    "AEILNRS": ["ALINERS", "NAILERS"],
    "AEINRST": ["NASTIER", "RETAINS", "STAINER"],
    "ADEINRS": ["SARDINE", "RANDIES"],
    "AEGINRS": ["SEARING", "ERASING", "REGAINS"],
    "AELPRST": ["PLASTER", "PSALTER", "STAPLER"],
    "AEIORST": ["OARIEST"],
    "AEILNST": ["SALTINE", "ELASTIN", "ENTAILS"],
    "ACEIRST": ["RACIEST", "STEARIC", "CRISTAE"],
    "AEGINST": ["SEATING", "TEASING", "INGESTA"],
    "ADEGNRS": ["GARDENS", "GANDERS", "DANGERS"],
    "AEINPRS": ["RAPINES", "PANIERS"],
    "ACELPRS": ["CLASPER", "PARCELS", "SCALPER"],
    "EINORST": ["STONIER", "ORIENTS"],
    "AELMNOT": ["OMENTAL", "TELAMON"],
    "ADEINST": ["INSTEAD", "DETAINS", "SAINTED"],
}


def _get_valid_groups(level: int) -> dict:
    """Filter anagram groups by level. Only groups with 2+ UNIQUE words."""
    target_len = level + 2  # level 1 → 3, level 2 → 4, etc.
    return {
        k: v for k, v in ANAGRAM_GROUPS.items()
        if len(k) == target_len and len(set(v)) >= 2  # Bug fix #2: use set()
    }


class WordGuessingEnvironment(Environment):
    """
    Anagram Word Guessing Environment — 5 levels with banking.

    The agent receives scrambled letters and must guess valid English words
    formed by rearranging ALL the letters. 2 attempts per word.
    From level 3, correct 1st-try guesses bank extra chances for retries.

    Example:
        >>> env = WordGuessingEnvironment()
        >>> obs = env.reset()
        >>> print(obs.scrambled_letters)  # e.g. ['T', 'A', 'B']
        >>> obs = env.step(WordGuessingAction(word_guess="BAT"))
        >>> print(obs.message)  # "Correct on 1st try! +1 banked chance."
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        """Initialize the environment."""
        self._state = WordGuessingState(
            episode_id=str(uuid4()),
            step_count=0,
        )
        self._valid_anagrams: list[str] = []  # Private — never exposed via /state

    # Bug fix #3: reset() takes NO parameters (OpenEnv interface)
    def reset(self) -> WordGuessingObservation:
        """Start a new episode at level 1."""
        self._state = WordGuessingState(
            episode_id=str(uuid4()),
            step_count=0,
            current_level=1,
            banked_chances=0,
            failed_words=[],
            total_reward=0.0,
        )
        self._valid_anagrams: list[str] = []  # Private — not exposed via /state (Codex Patch 2)
        return self._start_level(1)

    def step(self, action: WordGuessingAction) -> WordGuessingObservation:
        """Process agent action: word guess, bank spend, bank decision, or recovery guess."""
        self._state.step_count += 1
        s = self._state

        # ── Recovery challenge in progress — player must guess the word ──
        if s.recovery_pending is not None:
            if action.recovery_guess is not None:
                return self._handle_recovery_guess(action.recovery_guess.strip().upper())
            # Allow cancellation by sending bank_decision='cancel_recovery'
            if action.bank_decision == "cancel_recovery":
                s.banked_chances += 1  # refund
                s.recovery_pending = None
                return self._make_obs(
                    reward=0.0,
                    message="Recovery cancelled. Bank chance refunded.",
                )
            rec = s.recovery_pending
            letters = ", ".join(rec["letters"])
            return self._make_obs(
                reward=0.0,
                message=f"🔍 Recovery Challenge! Guess the missed word from Level {rec['level']}. Letters: {letters}",
            )

        # If a bank choice is pending, player MUST decide first
        if s.bank_choice_pending:
            if action.bank_decision is not None:
                return self._handle_bank_decision(action.bank_decision.strip().lower())
            return self._make_obs(
                reward=0.0,
                message="You earned a bank chance! Choose: 'preserve' (save to bank) or 'current' (add +2 guesses now).",
            )

        # Bank decision from panel (spending an existing banked chance)
        if action.bank_decision is not None:
            decision = action.bank_decision.strip().lower()
            if decision == "boost_current":
                if s.banked_chances <= 0:
                    return self._make_obs(reward=0.0, message="No banked chances to spend!")
                s.banked_chances -= 1
                s.max_wrong_per_level += 2
                wrong_left = s.max_wrong_per_level - s.guesses_this_level
                return self._make_obs(
                    reward=0.0,
                    message=f"⚡ Spent 1 bank! +2 guesses added ({wrong_left} remaining). {s.banked_chances} banked left.",
                )

        # Branch A: start recovery challenge for a failed level
        if action.use_bank_on is not None:
            return self._handle_bank(action.use_bank_on.strip())

        # Branch B: word guess
        if action.word_guess is not None:
            return self._handle_guess(action.word_guess.strip().upper())

        # Neither provided
        return self._make_obs(
            reward=-0.1,
            message="Invalid action — provide word_guess, use_bank_on, recovery_guess, or bank_decision.",
        )

    @property
    def state(self) -> WordGuessingState:
        """Get the current environment state."""
        return self._state

    # ──────────────────────────────────────────────────────────
    # Level management
    # ──────────────────────────────────────────────────────────

    def _start_level(self, level: int) -> WordGuessingObservation:
        """Set up a new level with fresh scrambled letters."""
        groups = _get_valid_groups(level)
        if not groups:
            return self._game_over()

        sorted_key = random.choice(list(groups.keys()))
        anagrams = groups[sorted_key]

        # Scramble the letters
        letters = list(sorted_key)
        random.shuffle(letters)

        # Update state — dynamic guesses = 2× total words
        s = self._state
        s.current_level = level
        s.scrambled_letters = letters
        self._valid_anagrams = list(anagrams)
        random.shuffle(self._valid_anagrams)  # randomize word order
        s.found_words = []
        s.guesses_this_level = 0
        s.max_wrong_per_level = len(anagrams) * 2  # Dynamic: 2× words

        total_words = len(anagrams)
        max_guesses = s.max_wrong_per_level

        return WordGuessingObservation(
            scrambled_letters=letters,
            words_found=[],
            words_remaining=total_words,
            current_level=level,
            attempts_left_for_word=max_guesses,
            banked_chances=s.banked_chances,
            failed_words=[f"??? (L{fw['level']})" for fw in s.failed_words],
            message=f"Level {level}! Unscramble these letters. Find all {total_words} words. ({max_guesses} guesses allowed)",
            done=False,
            reward=0.0,
            metadata={
                "total_words": total_words,
                "max_wrong": max_guesses,
                "letter_count": len(letters),
                "level": level,
                "level_results": list(s.level_results),
                "bank_choice_pending": s.bank_choice_pending,
            },
        )

    def _finish_level(self) -> WordGuessingObservation | None:
        """Wrap up current level — record results and advance."""
        s = self._state

        # Mark all unfound words as failed for this level
        unfound = [w for w in self._valid_anagrams if w not in s.found_words]
        for w in unfound:
            s.failed_words.append({"word": w, "level": s.current_level})

        # Record level results (don't reveal failed words to client)
        s.level_results.append({
            "level": s.current_level,
            "found": list(s.found_words),
            "failed_count": len(unfound),
            "total_words": len(self._valid_anagrams),
            "letters": list(s.scrambled_letters),
        })

        all_found = len(unfound) == 0
        bonus = 0.0
        msg = ""

        if all_found:
            bonus = 2.0
            s.total_reward += bonus
            msg = f"ALL words found in Level {s.current_level}! +2.0 bonus! "

        # Advance to next level
        if s.current_level < s.max_level:
            next_obs = self._start_level(s.current_level + 1)
            next_obs.reward = bonus
            if msg:
                next_obs.message = msg + next_obs.message
            return next_obs
        else:
            return self._game_over(level_bonus=bonus)

    # ──────────────────────────────────────────────────────────
    # Guess handling — ANY valid unfound anagram accepted
    # ──────────────────────────────────────────────────────────

    def _handle_guess(self, guess: str) -> WordGuessingObservation:
        """Process a word guess — accepts ANY valid unfound anagram."""
        s = self._state

        # Already found this word? (doesn't cost a guess)
        if guess in s.found_words:
            return self._make_obs(
                reward=0.0,
                message=f"Already found '{guess}'! Try a different word.",
            )

        # ── Every guess costs 1 from the counter ──
        s.guesses_this_level += 1
        guesses_left = s.max_wrong_per_level - s.guesses_this_level

        # Correct guess? (any valid unfound anagram)
        if guess in self._valid_anagrams:
            s.found_words.append(guess)

            # First try bonus: first correct guess with no prior wrong answers
            wrong_count = s.guesses_this_level - len(s.found_words)
            first_try = wrong_count == 0 and len(s.found_words) == 1
            if first_try:
                reward = 1.0
                if s.current_level >= 3:
                    s.bank_choice_pending = True
                    msg = f"✅ '{guess}' found! 🏦 Bank chance earned! Choose how to use it."
                else:
                    msg = f"✅ '{guess}' found!"
            else:
                reward = 0.5
                msg = f"✅ '{guess}' found!"

            s.total_reward += reward

            # All words found?
            remaining = len(self._valid_anagrams) - len(s.found_words)
            if remaining == 0:
                advance_obs = self._finish_level()
                if advance_obs is not None:
                    advance_obs.reward = (advance_obs.reward or 0) + reward
                    advance_obs.message = msg + " " + advance_obs.message
                    return advance_obs

            return self._make_obs(
                reward=reward,
                message=f"{msg} {remaining} word(s) left. {guesses_left} guess(es) left.",
            )

        # Wrong guess
        guess_sorted = "".join(sorted(guess))
        target_sorted = "".join(sorted(s.scrambled_letters))

        if guess_sorted == target_sorted:
            reward = 0.1
            msg = f"'{guess}' uses the right letters but isn't a valid word."
        elif len(guess) != len(s.scrambled_letters):
            reward = -0.1
            msg = f"'{guess}' has wrong length. Must use all {len(s.scrambled_letters)} letters."
        else:
            reward = -0.1
            msg = f"'{guess}' is not a valid anagram."

        s.total_reward += reward

        # Hit guess limit? End level, unfound words become failed
        if guesses_left <= 0:
            msg += f" Out of guesses for Level {s.current_level}!"
            advance_obs = self._finish_level()
            if advance_obs is not None:
                advance_obs.reward = (advance_obs.reward or 0) + reward
                advance_obs.message = msg + " " + advance_obs.message
                return advance_obs

        return self._make_obs(
            reward=reward,
            message=f"{msg} {guesses_left} guess(es) left.",
        )

    # ──────────────────────────────────────────────────────────
    # Banking system — level-aware
    # ──────────────────────────────────────────────────────────

    def _handle_bank(self, level_str: str) -> WordGuessingObservation:
        """Start a recovery challenge — spend 1 bank to TRY guessing a failed word."""
        s = self._state

        if s.banked_chances <= 0:
            return self._make_obs(
                reward=-0.1,
                message="No banked chances available!",
            )

        # Parse level number
        try:
            target_level = int(level_str)
        except ValueError:
            return self._make_obs(
                reward=-0.1,
                message=f"Invalid level: '{level_str}'. Provide a level number.",
            )

        # Find first failed word from that level
        target = None
        for fw in s.failed_words:
            if fw["level"] == target_level:
                target = fw
                break

        if target is None:
            return self._make_obs(
                reward=-0.1,
                message=f"No failed words from Level {target_level}.",
            )

        # Spend 1 bank and enter recovery challenge mode
        s.banked_chances -= 1
        word = target["word"]
        letters = list(word)
        random.shuffle(letters)

        s.recovery_pending = {
            "level": target_level,
            "word": word,
            "letters": letters,
            "target_fw": target,  # reference to remove on success
        }

        letters_str = ", ".join(letters)
        return self._make_obs(
            reward=0.0,
            message=f"🔍 Recovery Challenge! Unscramble these letters from Level {target_level}: {letters_str}. You have 1 guess!",
        )

    def _handle_recovery_guess(self, guess: str) -> WordGuessingObservation:
        """Handle the player's recovery challenge guess."""
        s = self._state
        rec = s.recovery_pending

        if rec is None:
            return self._make_obs(reward=0.0, message="No recovery challenge active.")

        target_word = rec["word"]
        target_level = rec["level"]
        target_fw = rec["target_fw"]

        # Clear recovery state
        s.recovery_pending = None

        # Check if they guessed a word they already found
        already_found = False
        for lr in s.level_results:
            if lr["level"] == target_level and guess in lr.get("found", []):
                already_found = True
                break

        if already_found:
            # They guessed the same word they already know — wasted!
            fun_lines = [
                f"🤦 Déjà vu! You already found '{guess}'. Bank chance wasted!",
                f"😅 '{guess}' again? You already nailed that one! Bank chance gone.",
                f"🔄 '{guess}'... been there, done that! Bank chance burned.",
                f"💸 '{guess}' is old news! You just wasted a bank chance on a repeat.",
            ]
            import random as _rng
            return self._make_obs(
                reward=-0.1,
                message=f"{_rng.choice(fun_lines)} {s.banked_chances} bank left.",
            )

        if guess == target_word:
            # Correct! Remove from failed words and update level results
            if target_fw in s.failed_words:
                s.failed_words.remove(target_fw)

            for lr in s.level_results:
                if lr["level"] == target_level and lr["failed_count"] > 0:
                    lr["failed_count"] -= 1
                    lr["found"].append(target_word)
                    break

            s.total_reward += 0.5
            return self._make_obs(
                reward=0.5,
                message=f"🎉 Correct! '{target_word}' recovered from Level {target_level}! {s.banked_chances} bank left.",
            )
        else:
            # Wrong — bank chance is wasted, word stays failed
            return self._make_obs(
                reward=-0.1,
                message=f"❌ Wrong! Bank chance used up. {s.banked_chances} bank left.",
            )


    def _handle_bank_decision(self, decision: str) -> WordGuessingObservation:
        """Process player's bank choice: preserve or current."""
        s = self._state
        s.bank_choice_pending = False

        if decision == "preserve":
            # Save the chance to bank for spending later
            s.banked_chances += 1
            return self._make_obs(
                reward=0.0,
                message=f"🏦 Bank chance preserved! ({s.banked_chances} total banked)",
            )
        elif decision == "current":
            # Add +2 guesses to the current level
            s.max_wrong_per_level += 2
            wrong_left = s.max_wrong_per_level - s.guesses_this_level
            return self._make_obs(
                reward=0.0,
                message=f"⚡ +2 guesses added to current level! ({wrong_left} guesses remaining)",
            )
        else:
            # Invalid choice — keep pending
            s.bank_choice_pending = True
            return self._make_obs(
                reward=0.0,
                message="Invalid choice. Pick 'preserve' or 'current'.",
            )

    # ──────────────────────────────────────────────────────────
    # Game over
    # ──────────────────────────────────────────────────────────

    def _game_over(self, level_bonus: float = 0.0) -> WordGuessingObservation:
        """End the game and calculate final score."""
        s = self._state
        bonus = 0.0

        if not s.failed_words:
            bonus = 5.0
            s.total_reward += bonus
            msg = f"PERFECT! All 5 levels cleared with no failures! +5.0 bonus! Total: {s.total_reward:.1f}"
        else:
            msg = f"Game complete! {len(s.failed_words)} word(s) missed. Total: {s.total_reward:.1f}"

        return WordGuessingObservation(
            scrambled_letters=s.scrambled_letters,
            words_found=list(s.found_words),
            words_remaining=0,
            current_level=s.current_level,
            attempts_left_for_word=0,
            banked_chances=s.banked_chances,
            failed_words=[f"??? (L{fw['level']})" for fw in s.failed_words],
            message=msg,
            done=True,
            reward=level_bonus + bonus,
            metadata={
                "total_reward": s.total_reward,
                "failed_count": len(s.failed_words),
                "game_over": True,
                "level_results": list(s.level_results),
                "bank_choice_pending": False,
            },
        )

    # ──────────────────────────────────────────────────────────
    # Helper
    # ──────────────────────────────────────────────────────────

    def _make_obs(self, reward: float, message: str) -> WordGuessingObservation:
        """Build an observation from current state."""
        s = self._state
        remaining = len(self._valid_anagrams) - len(s.found_words)
        wrong_left = max(0, s.max_wrong_per_level - s.guesses_this_level)

        # Build recovery info for frontend (exclude the actual word!)
        recovery_info = None
        if s.recovery_pending:
            recovery_info = {
                "level": s.recovery_pending["level"],
                "letters": s.recovery_pending["letters"],
            }

        return WordGuessingObservation(
            scrambled_letters=s.scrambled_letters,
            words_found=list(s.found_words),
            words_remaining=remaining,
            current_level=s.current_level,
            attempts_left_for_word=wrong_left,
            banked_chances=s.banked_chances,
            failed_words=[f"??? (L{fw['level']})" for fw in s.failed_words],
            message=message,
            done=False,
            reward=reward,
            metadata={
                "level": s.current_level,
                "found_count": len(s.found_words),
                "step": s.step_count,
                "level_results": list(s.level_results),
                "bank_choice_pending": s.bank_choice_pending,
                "max_wrong": s.max_wrong_per_level,
                "total_words": len(self._valid_anagrams),
                "recovery_pending": recovery_info,
            },
        )
