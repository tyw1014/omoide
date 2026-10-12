# Three-minute Omoide demonstration

Use the fictional dataset and keep **Demo Mode** selected. Record the browser window on your own machine. No cloud key or GPU is needed.

| Time | Action | Suggested English narration |
| --- | --- | --- |
| 0:00–0:20 | Show the memory feed and tagline. | “We capture small moments, but they disappear into scattered notes. Omoide helps turn the moments we choose to record into stories we can revisit.” |
| 0:20–0:55 | Add a memory dated October 10, 2026: “First time I scored a buzzer-beating three-pointer playing basketball with friends!” Save and show the original and metadata. | “I can save a moment in my own words. The original stays separate from the organized metadata. This demo uses labeled offline rules; live structured AI is available only with explicit opt-in.” |
| 0:55–1:25 | Open Rewind. Choose Weekly, October 10, 2026, and Generate recap. Then briefly select Monthly. | “These counts come directly from the recorded events, not an AI estimate. I can revisit a week, month, or year. The story links to the records supporting it.” |
| 1:25–2:15 | Open Life chapters. Expand My Basketball Journey, review the suggested members, and create the chapter. Generate chapter story. Scroll its timeline. | “The main idea is Life Chapters. Basketball memories from different dates become one thread. I choose which records belong, and I can change membership.” |
| 2:15–2:40 | Use Open original or a source button. Show the original description and edit controls. | “Every generated story leads back to an original memory. I can correct metadata or remove a record. Omoide organizes what I recorded, without pretending it knows my entire life.” |
| 2:40–3:00 | Return to the chapter or home. | “This is a working single-user Streamlit and SQLite MVP. Stage II will explore private local inference on the ASUS UGen Intel Arc Pro B70. Hardware compatibility and performance still need verification.” |

## Preparation

1. Run the README setup commands and load **Synthetic Demo Data**.
2. Check that the sample feed contains 36 records. September has 26; October has 10; October 5–11 has 6 before adding your own example.
3. Leave the Basketball suggestion unconfirmed until filming; delete an old demo chapter if you have rehearsed it. Deleting a chapter preserves its memories.
4. Keep the new capture date inside October 5–11 so the weekly recap includes it.
5. Label the dataset fictional and processing rule-based during the video. Do not present the prototype as verified Intel GPU inference.

## Short proposal outline

1. **Problem:** meaningful everyday memories remain fragmented and difficult to revisit.
2. **Solution:** voluntary capture → structured organization → period recaps → thematic Life Chapters.
3. **Differentiation:** connect records across dates while preserving originals and visible source references.
4. **Current implementation:** working local MVP; optional cloud API adapter with opt-in; key-free offline demo.
5. **Stage II:** evaluate a local inference provider on the designated hardware, then consider image and voice processing.
