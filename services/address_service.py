import re

class AddressService:
    # Ordena as vias de um cruzamento alfabeticamente para evitar "Via A & Via B" vs "Via B & Via A"
    ORDENAR_VIAS_CRUZAMENTO = True

    # Converte endereços sem nº predial do tipo "Av. X, a 95m da Rua Y" / "150m antes da R. Y" em Cruzamento
    CONVERTER_REFERENCIA_TRANSVERSAL_EM_CRUZAMENTO = True

    # Preserva o número predial quando houver deslocamento em metros (ex: "Nº 778 mais 3 metros" -> "778")
    PRESERVAR_NUMERO_COM_DESLOCAMENTO = False

    # 1. Tipos de via: expandidos apenas no início de cada logradouro
    PREFIXOS_VIA = [
        (r"^(?:ESTR|ESTRADA)\.?\s*MUN(?:ICIPAL)?\b\.?", "Estrada Municipal"),
        (r"^(?:ESTR|ESTRADA)\b\.?", "Estrada"),
        (r"^(?:AV|AVEN|AVENIDA)\b\.?", "Avenida"),
        (r"^(?:R|RUA)\b\.?", "Rua"),
        (r"^(?:PÇA|PCA|PC|PRAÇA|PRACA)\b\.?", "Praça"),
        (r"^(?:AL|ALAMEDA)\b\.?", "Alameda"),
        (r"^(?:VD|VIADUTO)\b\.?", "Viaduto"),
        (r"^(?:TV|TRAV|TRAVESSA)\b\.?", "Travessa"),
        (r"^(?:ROD|RODOVIA)\b\.?", "Rodovia"),
        (r"^(?:ALÇA|ALCA)\s+(?:DE\s+)?ACESSO\b", "Alça de Acesso"),
    ]

    # 2. Títulos e abreviações de nomes
    TITULOS = [
        (r"\b(?:DR\s*\.?\s*ª|DRA)\b\.?", "Doutora"),
        (r"\bDR\b\.?", "Doutor"),
        (r"\b(?:PROF\s*\.?\s*ª|PROFA)\b\.?", "Professora"),
        (r"\bPROF[º°]?\b\.?(?=\s+(?:ESCOL[ÁA]STICA|OLINDA|ELISABETH|MARIA|ANA|L[ÚU]CIA))", "Professora"),
        (r"\bPROF[º°]?\b\.?", "Professor"),
        (r"\b(?:ENG\s*\.?\s*ª|ENGA)\b\.?", "Engenheira"),
        (r"\bENG[º°]?\b\.?", "Engenheiro"),
        (r"\bCEL\b\.?", "Coronel"),
        (r"\bBRIG\b\.?", "Brigadeiro"),
        (r"\bGEN\b\.?", "General"),
        (r"\bMAL\b\.?|\bMARECHAL\b", "Marechal"),
        (r"\bCAP\b\.?", "Capitão"),
        (r"\bTEN\b\.?", "Tenente"),
        (r"\bSGT\b\.?", "Sargento"),
        (r"\bSUBTEN\b\.?", "Subtenente"),
        (r"\bSEN\b\.?", "Senador"),
        (r"\bDEP\b\.?", "Deputado"),
        (r"\bGOV\b\.?", "Governador"),
        (r"\bPRES\b\.?", "Presidente"),
        (r"\bPREF\b\.?", "Prefeito"),
        (r"\bVER\b\.?", "Vereador"),
        (r"\bMONS\b\.?", "Monsenhor"),
        (r"\bCON\b\.?|\bCÔN\b\.?", "Cônego"),
        (r"\bPE\b\.?|\bPADRE\b", "Padre"),
        (r"\bME\b\.?|\bMADRE\b", "Madre"),
        (r"\bFR\b\.?(?=\s+DA\s+ROSA)", "Francisca"),
        (r"\bFR\b\.?|\bFREI\b", "Frei"),
        (r"\bSTA\b\.?", "Santa"),
        (r"\bSTO\b\.?", "Santo"),
        (r"\bJR\b\.?|\bJUNIOR\b", "Júnior"),
        (r"\bJD\b\.?", "Jardim"),
        (r"\bVL\b\.?", "Vila"),
        (r"\bPQ\b\.?", "Parque"),
        (r"\bVD\b\.?", "Viaduto"),
        (r"\bHENR\b\.?", "Henrique"),
        (r"\bFERN\b\.?", "Fernandes"),
        (r"\bROD\b\.(?=\s+CASTELLI)", "Rodolfo"),
    ]

    # 3. Correções de acentuação e grafia recorrentes na base do RBMLQ
    CORRECOES_ORTOGRAFICAS = [
        (r"\bSAO\b", "São"),
        (r"\bJOAO\b", "João"),
        (r"\bJOSE\b", "José"),
        (r"\bANTONIO\b", "Antônio"),
        (r"\bMARIO\b", "Mário"),
        (r"\bEMILIO\b", "Emílio"),
        (r"\bJANUARIO\b", "Januário"),
        (r"\bGETULIO\b", "Getúlio"),
        (r"\bITALIA\b", "Itália"),
        (r"\bINDEPENDENCIA\b", "Independência"),
        (r"\bDIVISAO\b", "Divisão"),
        (r"\bBARAO\b", "Barão"),
        (r"\bJACAREI\b", "Jacareí"),
        (r"\bESCOLASTICA\b", "Escolástica"),
        (r"\bVOLUNTARIO\b|\bVOLUNTÁRIOS\b", "Voluntário"),
        (r"\bSERGIO\b", "Sérgio"),
        (r"\bESPIRIO\b", "Espírito"),
        (r"\bRAÚL\b", "Raul"),
        (r"\bTHEREZA\b", "Teresa"),
        (r"\bORESTES\b(?=\s+GIRARDI)", "Oreste"),
        (r"\bGIRALDI\b", "Girardi"),
        (r"\bALVARO\b", "Álvaro"),
        (r"\bALVARES\b", "Álvares"),
        (r"\bLAZAROS\b", "Lázaros"),
        (r"\bLUCIO\b", "Lúcio"),
        (r"\bJOSUE\b", "Josué"),
        (r"\bMOISES\b", "Moisés"),
        (r"\bCESAR\b", "César"),
        (r"\bCECILIA\b", "Cecília"),
        (r"\bAVARISTO\b", "Evaristo"),
        (r"\bCHATEUBRIAND\b", "Chateaubriand"),
        (r"\bSCHNNEIDER\b", "Schneider"),
        (r"\bATANAZIO\b", "Atanázio"),
        (r"\bNESTLE\b", "Nestlé"),
        (r"\bPENSYLVANIA\b", "Pensilvânia"),
        (r"\bJERONYMO\b", "Jerônimo"),
    ]

    # 4. Unificação canônica de logradouros com múltiplas grafias na mesma cidade
    CANONIZACAO_VIAS = [
        # São José dos Campos
        (r"^Avenida (?:Doutor )?Sebastião H(?:enrique)?\.?\s*(?:da\s*)?C(?:unha)?\.?\s*Pontes$", "Avenida Doutor Sebastião Henrique da Cunha Pontes"),
        (r"^Avenida Doutor João B(?:atista)?\.?\s*(?:de\s+)?S(?:ouza)?\.?\s*Queiroz Júnior$", "Avenida Doutor João Batista de Souza Queiroz Júnior"),
        (r"^Alça de Acesso Professora Elisabeth G(?:uimarães)?\.?\s*Baruel$", "Alça de Acesso Professora Elisabeth Guimarães Baruel"),
        (r"^Avenida Isaur de P(?:inho)?\.?\s*Nogueira$", "Avenida Isaur de Pinho Nogueira"),
        (r"^Avenida Leonor de A(?:lmeida)?\.?\s*R(?:ibeiro)?\.?\s*Souto$", "Avenida Leonor de Almeida Ribeiro Souto"),
        (r"^Estrada Municipal Ubirajara (?:de\s+)?O(?:liveira)?\.?\s*Pinto$", "Estrada Municipal Ubirajara de Oliveira Pinto"),
        (r"^Rua Raul F(?:ranco)?\.?\s*Martins$", "Rua Raul Franco Martins"),
        (r"^Avenida (?:Doutor )?Eduardo Cury$", "Avenida Doutor Eduardo Cury"),
        (r"^Avenida (?:dos )?Sindicalistas$", "Avenida dos Sindicalistas"),
        (r"^(?:Avenida|Estrada Municipal) Dom José Antônio do Couto$", "Avenida Dom José Antônio do Couto"),
        (r"^Avenida Madre Teresa(?:\s+de\s+Calcutá)?$", "Avenida Madre Teresa de Calcutá"),
        # Taubaté
        (r"^Avenida (?:dos )?Bandeirantes$", "Avenida dos Bandeirantes"),
        (r"^Avenida Dom Pedro(?:\s+I)?$", "Avenida Dom Pedro I"),
        (r"^Avenida Reitor Milton de F(?:aria)?\.?\s*Chagas$", "Avenida Reitor Milton de Faria Chagas"),
        (r"^Avenida Jorge S(?:alim)?\.?\s*Mutran$", "Avenida Jorge Salim Mutran"),
        (r"^Praça (?:8|Oito) de Maio$", "Praça Oito de Maio"),
        (r"^Avenida (?:Padre Hugo Bertonazzi|do Pinhão)$", "Avenida Padre Hugo Bertonazzi"),
        # Jacareí / Guaratinguetá / Pindamonhangaba / Campos do Jordão / Caçapava
        (r"^Avenida Senador Joaquim M(?:iguel)?\.?\s*M(?:artins)?\.?\s*de Siqueira$", "Avenida Senador Joaquim Miguel Martins de Siqueira"),
        (r"^Avenida (?:Governador )?Mário Covas$", "Avenida Governador Mário Covas"),
        (r"^Avenida (?:Presidente )?(?:JK|Juscelino K(?:ubitschek)?\.?)\s+de Oliveira$", "Avenida Presidente Juscelino Kubitschek de Oliveira"),
        (r"^Avenida Octavio R(?:odrigues)?\.?\s+da Silva$", "Avenida Octavio Rodrigues da Silva"),
        (r"^Avenida Padre José Maria G(?:uimarães)?\.?\s*Alves$", "Avenida Padre José Maria Guimarães Alves"),
        (r"^Estrada Municipal (?:Abade )?Biagino Chieffi$", "Estrada Municipal Abade Biagino Chieffi"),
        (r"^Estrada (?:Municipal )?Sebastião Vieira Machado$", "Estrada Municipal Sebastião Vieira Machado"),
        (r"^Avenida Wilson N(?:ogueira)?\.?\s*Soares$", "Avenida Wilson Nogueira Soares"),
        (r"^(?:Avenida|Rua) Brigadeiro Jordão$", "Rua Brigadeiro Jordão"),
        (r"^(?:Avenida|Rua) Frei Oreste Girardi$", "Avenida Frei Oreste Girardi"),
        (r"^(?:Avenida|Rua) Doutor José de Moura Resende$", "Avenida Doutor José de Moura Resende"),
    ]

    @staticmethod
    def _normalizar_espacos_e_milhar(texto: str) -> str:
        texto = re.sub(r"\.([A-Za-zÀ-ÖØ-öø-ÿ])", r". \1", texto)
        texto = re.sub(r"\b(\d{1,2})\.(\d{3})\b", r"\1\2", texto)
        return texto

    @staticmethod
    def _title_case_pt(texto: str) -> str:
        palavras = texto.split()
        menores = {"de", "da", "do", "das", "dos", "e", "em", "com", "para", "por", "ao", "aos", "na", "no", "nas", "nos", "a", "o"}
        romanos = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xv", "xx", "xxi", "jk"}
        resultado = []
        for i, p in enumerate(palavras):
            p_clean = p.strip(".,()-")
            p_lower = p_clean.lower()
            if p_lower in romanos:
                resultado.append(p_clean.upper())
            elif len(p_clean) == 1 and p.endswith("."):
                resultado.append(p.upper())
            elif i > 0 and p_lower in menores:
                resultado.append(p_lower)
            elif "'" in p:
                resultado.append("'".join(parte.capitalize() for parte in p.split("'")))
            else:
                resultado.append(p.capitalize())
        return " ".join(resultado)

    @classmethod
    def _formatar_nome_via(cls, via_raw: str, exigir_tipo_via: bool = False) -> str:
        via = cls._normalizar_espacos_e_milhar(via_raw).strip(" ,.-/¿?()")
        via = re.sub(r"^(?:A|O)\s+(?=(?:RUA|R\.|AV|AVENIDA|ESTR|PRAÇA|PCA|PÇA|ALAMEDA|VIADUTO|VD)\b)", "", via, flags=re.IGNORECASE)

        teve_prefixo = False
        for padrao, subst in cls.PREFIXOS_VIA:
            if re.search(padrao, via, flags=re.IGNORECASE):
                via = re.sub(padrao, subst + " ", via, count=1, flags=re.IGNORECASE)
                teve_prefixo = True
                break

        if exigir_tipo_via and not teve_prefixo and not re.match(r"^(?:VIA|PASSARELA|LARGO|BECO)\b", via, re.IGNORECASE):
            via = "Rua " + via

        for padrao, subst in cls.TITULOS:
            via = re.sub(padrao, subst, via, flags=re.IGNORECASE)

        for padrao, subst in cls.CORRECOES_ORTOGRAFICAS:
            via = re.sub(padrao, subst, via, flags=re.IGNORECASE)

        via = re.sub(r"\s+", " ", via).strip(" ,.-/¿?")
        via_tc = cls._title_case_pt(via)

        for padrao, subst in cls.CANONIZACAO_VIAS:
            if re.match(padrao, via_tc, flags=re.IGNORECASE):
                via_tc = subst
                break

        return via_tc

    @staticmethod
    def _limpar_complementos_via(texto: str) -> str:
        res = texto
        padroes_corte = [
            r"\s*\(.*?\)",
            r"¿.*$",
            r"(?i)[,\s-]*\b(?:pr[óo]x(?:imo)?|oposto|defronte|em\s+frente|alt(?:ura)?|aprox(?:imadamente)?)\b.*$",
            r"(?i)[,\s-]*\b(?:mais|menos|antes|ap[óo]s|depois|cerca\s+de)\b.*$",
            r"(?i)[,\s-]*\+\s*\d+\s*(?:m|metros?|metro)?\b.*$",
            r"(?i)[,\s-]*\b(?:a\s+)?\d+(?:[,\.]\d+)?\s*(?:m|metros?|metro)\b.*$",
            r"(?i)[,\s-]*\b(?:sentido|fx|faixa|pista|b/c|c/b|centro\s*/\s*bairro|bairro\s*/\s*centro|sa[íi]da\s+do\s+t[úu]nel)\b.*$",
            r"(?i)[,\s-]*\b(?:s/n[º°]?|km\s*\d+)\b.*$",
            r"(?i)\s*-\s*(?:vila|jd|jardim|ch[áa]cara|parque|centro|santa|são|sao|campos|taubat[ée]|jacare[íi]|caçapava|caraguatatuba|ubatuba|aparecida|guaratinguet[áa]|pindamonhangaba|nissan|cta|corpo\s+de\s+bombeiro|f\s*\d).*$",
            r"(?i)[,\s]+(?:n[º°\.]*|nr\.?|numeral)\s*\d+.*$",
            r"(?i)[,\s]+\d{1,5}\s*$",
        ]
        for p in padroes_corte:
            res = re.sub(p, "", res).strip(" ,.-/¿?()")
        return res

    @staticmethod
    def _padronizar_rodovia(nome_raw: str, municipio: str = "") -> str:
        nome = nome_raw.upper().replace("ROD.", "").replace("RODOVIA", "").strip()
        match_spa = re.search(r"\b(SPA|SPI)\s*[-/]?\s*(\d{1,3})\s*[/]\s*(\d{1,3})\b", nome)
        if match_spa:
            tipo, n1, n2 = match_spa.groups()
            return f"{tipo}-{int(n1):03d}/{int(n2):03d}"

        match_comum = re.search(r"\b(SP|BR)\s*[-/]?\s*(\d{1,3})\b", nome)
        if match_comum:
            tipo, num = match_comum.groups()
            num_int = int(num)
            if num_int == 488 and "APARECIDA" in str(municipio).upper():
                tipo = "BR"
            return f"{tipo}-{num_int:03d}"

        return nome

    @staticmethod
    def _extrair_km(texto: str):
        match_soma = re.search(r"KM[:\s]*(\d+)[\s]*\+[\s]*(\d+)", texto, re.IGNORECASE)
        if match_soma:
            return round(int(match_soma.group(1)) + (int(match_soma.group(2)) / 1000.0), 3)

        match_dec = re.search(r"KM[:\s]*(\d+)[,\.](\d+)", texto, re.IGNORECASE)
        if match_dec:
            return round(float(f"{int(match_dec.group(1))}.{match_dec.group(2)}"), 3)

        match_simples = re.search(r"KM[:\s]*(\d+)", texto, re.IGNORECASE)
        if match_simples:
            return round(float(match_simples.group(1)), 3)

        return None

    @staticmethod
    def _formatar_km_brasileiro(km_val) -> str:
        if km_val is None:
            return ""
        texto = f"{km_val:.3f}".rstrip("0").rstrip(".")
        return texto.replace(".", ",")

    @classmethod
    def processar_endereco(cls, local_verificacao: str, municipio: str, uf: str = "SP") -> dict:
        local_original = str(local_verificacao or "").strip()
        local_limpo = cls._normalizar_espacos_e_milhar(local_original)

        # 1. Rodovia
        is_rodovia = bool(
            re.search(r"\b(SP|BR|ROD|SPA|SPI)\s*[-/]?\s*\d{1,3}\b", local_limpo, re.IGNORECASE)
            and re.search(r"\bKM\b", local_limpo, re.IGNORECASE)
        )

        if is_rodovia:
            tipo_local = "Rodovia"
            rodovia_nome = cls._padronizar_rodovia(local_limpo, municipio)
            km_val = cls._extrair_km(local_limpo)
            km_str = cls._formatar_km_brasileiro(km_val)

            logradouro_limpo = f"{rodovia_nome} - KM {km_str}" if km_str else rodovia_nome
            numero_limpo = "S/N"
            km_num = km_val
            local_maps = f"{rodovia_nome}, KM {km_str}, {municipio} - {uf}" if km_str else f"{rodovia_nome}, {municipio} - {uf}"

        else:
            local_avaliar = re.split(r"\s+/\s+(?=(?:RUA|R\.|AV|PRAÇA|ESTR))", local_limpo, flags=re.IGNORECASE)[0]

            # Separadores explícitos de cruzamento
            sep_cruzamento = (
                r"\s+X\s+|\s+ESQ\.?\s+|\s+CRUZAMENTO\s+COM\s+|\s+INTERSE[ÇC][ÃA]O\s+|\s+INTERS\.?\s+"
                r"|\s+COM\s+(?=(?:A\s+)?(?:RUA|R\b\.?|AV\b\.?|AVENIDA|ESTR\b\.?|PRAÇA|PCA\b\.?|PÇA|ALAMEDA|VIA)\b)"
            )

            # Separadores de referência transversal (ex: "150m antes da R. Y", "a 95m da Av. Y", "após a Rua Y", "prox. ao viaduto Av. Y")
            sep_transversal = (
                r"(?:[,\s]+(?:a\s+)?\d+(?:[,\.]\d+)?\s*(?:m|metros?|metro)\s+(?:antes\s+da|ap[óo]s\s+a|da)\s+"
                r"|[,\s]+pr[óo]x\.?\s*ao\s+viaduto\s+"
                r"|\s+(?:antes\s+da|ap[óo]s\s+a)\s+)"
                r"(?=(?:RUA|R\b\.?|AV\b\.?|AVENIDA|ESTR\b\.?|PRAÇA|PCA\b\.?|PÇA|ALAMEDA))"
            )

            usar_transversal = (
                cls.CONVERTER_REFERENCIA_TRANSVERSAL_EM_CRUZAMENTO
                and bool(re.search(sep_transversal, local_avaliar, re.IGNORECASE))
            )

            if re.search(sep_cruzamento, local_avaliar, re.IGNORECASE) or usar_transversal:
                tipo_local = "Cruzamento"
                rodovia_nome = None
                km_num = None
                numero_limpo = "S/N"

                padrao_split = sep_cruzamento if re.search(sep_cruzamento, local_avaliar, re.IGNORECASE) else sep_transversal
                partes = re.split(padrao_split, local_avaliar, maxsplit=1, flags=re.IGNORECASE)
                via1 = cls._formatar_nome_via(cls._limpar_complementos_via(partes[0]), exigir_tipo_via=True)

                if len(partes) > 1 and partes[1].strip():
                    via2 = cls._formatar_nome_via(cls._limpar_complementos_via(partes[1]), exigir_tipo_via=True)
                    vias = sorted([via1, via2]) if cls.ORDENAR_VIAS_CRUZAMENTO else [via1, via2]
                    logradouro_limpo = f"{vias[0]} & {vias[1]}"
                else:
                    logradouro_limpo = via1

                local_maps = f"{logradouro_limpo}, {municipio} - {uf}"

            # 3. Urbano
            # 3. Urbano (ajuste opcional para máxima precisão no Google Maps)
            else:
                tipo_local = "Urbano"
                rodovia_nome = None
                km_num = None

                local_sem_parenteses = re.sub(r"\s*\(.*?\)", "", local_avaliar)

                # Só descarta o número se for 'oposto', 'próximo', 'em frente', 'defronte', 'altura' ou 's/n'
                tem_referencia_vaga = bool(
                    re.search(
                        r"(?i)\b(oposto|pr[óo]x(?:imo)?|defronte|em\s+frente|alt(?:ura)?|aprox(?:imadamente)?|s/n)\b",
                        local_sem_parenteses
                    )
                )

                # Procura número predial explícito (ex: "Nº 778 mais 3 metros" preserva o 778; "a 260m da..." vira S/N)
                match_num = re.search(
                    r"(?:[,\s]+(?:N[º°\.]*|NR\.?|NUMERAL)\s*|\s*,\s*)(\d{1,5})\b(?!\s*(?:m|metros?|metro|km)\b)",
                    local_sem_parenteses,
                    re.IGNORECASE
                )

                if not tem_referencia_vaga and match_num:
                    numero_limpo = str(int(match_num.group(1)))
                else:
                    numero_limpo = "S/N"

                nome_rua = cls._formatar_nome_via(cls._limpar_complementos_via(local_avaliar), exigir_tipo_via=True)
                logradouro_limpo = nome_rua

                # Na string de busca do Maps, omite ", S/N" para não poluir a query da API
                if numero_limpo == "S/N":
                    local_maps = f"{logradouro_limpo}, {municipio} - {uf}"
                else:
                    local_maps = f"{logradouro_limpo}, {numero_limpo}, {municipio} - {uf}"

        return {
            "tipo_local": tipo_local,
            "logradouro_limpo": logradouro_limpo,
            "numero_limpo": numero_limpo,
            "rodovia_nome": rodovia_nome,
            "km_num": km_num,
            "local_maps": local_maps,
            "UF": uf
        }