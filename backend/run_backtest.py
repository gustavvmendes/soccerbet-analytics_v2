"""Script standalone para rodar backtest e salvar resultado em JSON.

Executa o Backtester fora do contexto HTTP, com progresso no stdout.
Útil para gerar a tabela comparativa do TCC sem timeout do curl.
"""
import json
import sys
import time
from app import create_app
from app.ml.backtester import Backtester


def main():
    app = create_app()
    with app.app_context():
        seasons = [2025, 2026]
        if len(sys.argv) > 1:
            seasons = [int(s) for s in sys.argv[1].split(",")]

        print(f"=== Backtest comparativo: temporadas {seasons} ===")
        t0 = time.time()

        bt = Backtester(min_train_matches=80)
        results = bt.run(seasons)

        elapsed = time.time() - t0
        print(f"\n=== Concluído em {elapsed:.1f}s ===\n")

        # Salvar JSON completo
        out_path = "backtest_result.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Resultado salvo em: {out_path}\n")

        # Imprimir tabela-resumo
        print("=== TABELA COMPARATIVA ===")
        print(f"{'Modelo':<40} {'N':>5} {'Acc':>7} {'LogLoss':>9} {'Brier':>8} {'MAE_gols':>10}")
        print("-" * 82)
        for row in results.get("summary_table", []):
            print(f"{row['model']:<40} {row['n_predictions']:>5} "
                  f"{row['accuracy']*100:>6.1f}% {row['log_loss']:>9.4f} "
                  f"{row['brier_score']:>8.4f} {row['mae_goals_avg']:>10.3f}")


if __name__ == "__main__":
    main()
