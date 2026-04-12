import pdfplumber
import re
import os


class PDFService:
    PDF_DIR = "data/pdfs"

    @staticmethod
    def save_pdf(file_bytes: bytes, filename: str, match_id_prefix: str = "match") -> str:
        os.makedirs(PDFService.PDF_DIR, exist_ok=True)
        file_path = os.path.join(PDFService.PDF_DIR, f"{match_id_prefix}_{filename}")
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        return file_path

    @staticmethod
    def parse_femebal_sheet(pdf_file):
        data = {
            "match_info": {},
            "home_team": {"name": "", "players": []},
            "away_team": {"name": "", "players": []},
        }

        with pdfplumber.open(pdf_file) as pdf:
            page = pdf.pages[0]
            text = page.extract_text()
            tables = page.extract_tables()

            if not tables:
                return data

            players_table = None
            header_table = None
            score_table = None

            for table in tables:
                if not table:
                    continue

                first_row_str = " ".join([str(c) for c in table[0] if c]).lower()
                if "jugado en" in first_row_str or "cancha" in first_row_str:
                    header_table = table

                for row in table:
                    row_str = " ".join([str(c) for c in row if c]).lower()
                    if "equipo local" in row_str and "equipo visitante" in row_str:
                        score_table = table
                        break

                for i in range(min(3, len(table))):
                    row_str = " ".join([str(c) for c in table[i] if c]).lower()
                    if "local" in row_str and "visitante" in row_str and "n°" in row_str:
                        players_table = table
                        break

            if not players_table and tables:
                players_table = max(tables, key=len)
            if not header_table and tables:
                header_table = tables[0]

            # Parse match info from header table
            if header_table and len(header_table) > 1:
                try:
                    row = header_table[1]
                    if len(row) >= 6:
                        data["match_info"] = {
                            "venue": str(row[0]).strip(),
                            "court": str(row[1]).strip(),
                            "date": str(row[2]).strip(),
                            "time": str(row[3]).strip(),
                            "category": str(row[4]).strip(),
                            "match_number": str(row[5]).strip(),
                        }
                except Exception:
                    pass

            # Fallback regex on raw text
            if not data["match_info"].get("date") and text:
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
                if date_match:
                    data["match_info"]["date"] = date_match.group(1)

                time_match = re.search(r"(\d{2}:\d{2})", text)
                if time_match:
                    data["match_info"]["time"] = time_match.group(1)

                match_num = re.search(r"Partido\s*:?\s*(\d+)", text, re.IGNORECASE)
                if match_num:
                    data["match_info"]["match_number"] = match_num.group(1)

                cat_match = re.search(r"Categoria\s*-\s*Division\s*:?\s*(.*)", text, re.IGNORECASE)
                if cat_match:
                    data["match_info"]["category"] = cat_match.group(1).strip()

            # Parse scores
            if score_table:
                try:
                    for row in score_table:
                        if len(row) >= 6 and row[1] and row[4]:
                            h_score = PDFService._clean_int(row[2])
                            a_score = PDFService._clean_int(row[5])
                            data["match_info"]["home_score"] = h_score
                            data["match_info"]["away_score"] = a_score
                            data["home_team"]["name"] = str(row[1]).replace("Equipo local", "").strip()
                            data["away_team"]["name"] = str(row[4]).replace("Equipo visitante", "").strip()
                            break
                except Exception:
                    pass

            # Parse players
            if players_table:
                start_row_index = 0
                for i, row in enumerate(players_table):
                    row_str = " ".join([str(c) for c in row if c]).lower()
                    if "n°" in row_str:
                        start_row_index = i + 1
                        break

                for row in players_table[start_row_index:]:
                    if len(row) < 7:
                        continue
                    try:
                        if row[0] and row[1]:
                            p_local = PDFService._parse_player_row(row[0:7])
                            if p_local:
                                data["home_team"]["players"].append(p_local)
                    except IndexError:
                        pass

                    try:
                        if len(row) >= 14 and row[7] and row[8]:
                            p_away = PDFService._parse_player_row(row[7:14])
                            if p_away:
                                data["away_team"]["players"].append(p_away)
                    except IndexError:
                        pass

        return data

    @staticmethod
    def _parse_player_row(row):
        try:
            if not row[0]:
                return None
            number = str(row[0]).strip()
            if not number.isdigit():
                return None
            if not row[1]:
                return None
            name = str(row[1]).strip()
            goals = PDFService._clean_int(row[2])
            yellow = 1 if row[3] and str(row[3]).strip() not in ["-", ""] else 0
            two_min = PDFService._clean_int(row[4])
            red = 1 if row[5] and str(row[5]).strip() not in ["-", ""] else 0
            blue = 1 if row[6] and str(row[6]).strip() not in ["-", ""] else 0
            return {
                "number": int(number),
                "name": name,
                "goals": goals,
                "yellow": yellow,
                "two_min": two_min,
                "red": red,
                "blue": blue,
            }
        except Exception:
            return None

    @staticmethod
    def _clean_int(val) -> int:
        if not val:
            return 0
        val = str(val).strip()
        if val in ["-", "", "None"]:
            return 0
        try:
            return int(val)
        except ValueError:
            return 0
