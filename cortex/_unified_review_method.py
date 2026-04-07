    def _single_llm_review(self, indicators, z_base, best_name, best_sim, second_name, second_sim,
                           sim_adj, fresh, gap, penalty):
        """
        Revision LLM MINIMA — prompt telegrama, 0 JSON template.
        Input: ~60 tokens. Output: max 20 tokens.
        Total: ~80 tokens cuando se activa.

        Formato respuesta aceptado:
          - "same" -> mantener isomorfo
          - nombre isomorfo -> cambiar
          - opcionalmente una palabra de contradiccion despues
        """
        snapshot = self._compact_market_snapshot(indicators, fresh)
        z_deltas = self._compact_z_deltas(z_base, best_name)

        # Prompt telegrama — sin JSON template, sin ejemplos
        prompt = (
            f"top={best_name}({best_sim:.2f}) 2nd={second_name}({second_sim:.2f}) "
            f"gap={gap:.2f} pen={penalty:+.2f} {snapshot} dZ={z_deltas} "
            f"iso? extra?"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.REVIEW_MAX_TOKENS,
                temperature=0.0
            )
            token_tracker.add("unified", resp.usage.prompt_tokens, resp.usage.completion_tokens)

            raw = resp.choices[0].message.content.strip()
            logger.info(f"Unified review raw: '{raw[:60]}'")

            # Parse flexible: JSON o texto libre
            iso_result   = best_name
            contradiction = ""

            s = raw.find("{"); e = raw.rfind("}")
            if s != -1 and e > s:
                try:
                    data = json.loads(raw[s:e+1])
                    iso_result    = self._normalize_review_iso(data.get("iso","same"), best_name)
                    contradiction = str(data.get("x","")).strip()
                except Exception:
                    pass
            else:
                parts = raw.split(None, 1)
                if parts:
                    iso_result = self._normalize_review_iso(parts[0].strip(".,;:"), best_name)
                if len(parts) > 1:
                    contradiction = parts[1].strip()[:60]

            if contradiction.lower() in ("", "none", "null", "-", "no", "ninguna"):
                contradiction = ""

            logger.info(f"Unified review: iso={iso_result} x='{contradiction[:40]}'")
            return {"iso": iso_result, "contradiction": contradiction}

        except Exception as e:
            logger.warning(f"Unified review fallback: {e}")
            return {"iso": best_name, "contradiction": ""}
