from datetime import datetime

class TransformationLog: 
    def __init__(self):
        self.logs = []

    def adicionar(
        self,
        coluna: str,
        tipo_transformacao: str,
        antes: str,
        depois: str,
        detalhes: str
    ):
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "coluna": coluna,
            "tipo_transformacao": tipo_transformacao,
            "antes": antes,
            "depois": depois,
            "detalhes": detalhes
        })

    def obter_logs(self):
        return self.logs