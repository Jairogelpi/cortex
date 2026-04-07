    def _single_llm_review(self, indicators, z_base, best_name, best_sim, second_name, second_sim,
                           sim_adj, fresh, gap, penalty):
        """
        Revision LLM MINIMA: solo cuando hay ambiguedad real.
        
        OPTIMIZACION MAXIMA SIN PERDER POTENCIA:
        - Prompt: ~60 tokens input (notacion telegrama, sin JSON template)
        - Output: max_tokens=20 (solo "same"/"nombre_isomorfo" + palabra contradiccion)
        - Total: ~80 tokens si se activa, 0 si no hace falta
        
        El LLM solo responde dos cosas:
          1. ¿Cambiar isomorfo? -> "same" o nombre del isomorfo
          2. ¿Hay algo inesperado? -> 1-3 palabras o vacio
        """
        snapshot = self._compact_market_snapshot(indicators, fresh)
        z_deltas = self._compact_z_deltas(z_base, best_name)

        # Prompt telegrama — sin JSON template, sin ejemplos, sin instrucciones largas
        # El modelo entiende el formato por el contexto
        prompt = (
            f"top={best_name}({best_sim:.2f}) 2nd={second_name}({second_sim:.2f}) "
            f"gap={gap:.2f} pen={penalty:+.2f} adj={sim_adj:.2f} "
            f"{snapshot} dZ={z_deltas} "
            f"iso? extra?"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.REVIEW_MAX_TOKENS,  # 20 tokens
                temperature=0.0
            )
            token_tracker.add("unified", resp.usage.prompt_tokens, resp.usage.completion_tokens)

            raw = resp.choices[0].message.content.strip()
            logger.info(f"Unified review raw: '{raw[:60]}'")

            # Parse flexible: acepta JSON o texto libre
            iso_result = best_name
            contradiction = ""

            # Intentar JSON primero
            s = raw.find("{"); e = raw.rfind("}")
            if s != -1 and e > s:
                try:
                    data = json.loads(raw[s:e+1])
                    iso_result = self._normalize_review_iso(data.get("iso","same"), best_name)
                    contradiction = str(data.get("x","")).strip()
                except Exception:
                    pass
            else:
                # Texto libre: primera palabra = isomorfo o "same"
                parts = raw.split()
                if parts:
                    candidate = parts[0].strip(".,;:")
                    iso_result = self._normalize_review_iso(candidate, best_name)
                if len(parts) > 1:
                    contradiction = " ".join(parts[1:])[:60]

            if contradiction.lower() in ("", "none", "null", "empty", "ninguna", "no", "-"):
                contradiction = ""

            logger.info(f"Unified review: iso={iso_result} x='{contradiction[:40]}'")
            return {"iso": iso_result, "contradiction": contradiction}

        except Exception as e:
            logger.warning(f"Unified review fallback: {e}")
            return {"iso": best_name, "contradiction": ""}
