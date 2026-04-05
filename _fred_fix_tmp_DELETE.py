    def _fetch_fred_csv(self, series_id: str) -> Optional[float]:
        """Descarga serie FRED via CSV publico sin autenticacion."""
        try:
            import pandas as pd
            from io import StringIO
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
            headers = {"User-Agent": "CortexV2/1.0 (research)"}
            response = requests.get(url, headers=headers, timeout=self.API_TIMEOUT)
            if response.status_code != 200:
                return None
            # FRED CSV: primera columna DATE, segunda columna = valor
            # No usar parse_dates — leer raw y filtrar manualmente
            df = pd.read_csv(
                StringIO(response.text),
                na_values=[".", ""]
            )
            # La primera columna es DATE (nombre real del header)
            if df.empty or df.shape[1] < 2:
                return None
            # Filtrar filas con valores validos en la segunda columna
            df = df.dropna(subset=[df.columns[1]])
            if df.empty:
                return None
            return float(df.iloc[-1, 1])
        except Exception as e:
            logger.debug(f"FRED CSV {series_id} fallo: {e}")
            return None