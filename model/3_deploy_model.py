# model/3_deploy_model.py
# ─────────────────────────────────────────────────────────
# Copies trained model to backend and swaps in the ML scorer.
# Run from the model/ directory after training.
#
# Run: python 3_deploy_model.py
# ─────────────────────────────────────────────────────────

import shutil
import os

def main():
    print("=" * 50)
    print("SectorSignal — Deploy Model to Backend")
    print("=" * 50)

    # 1. Check model file exists
    if not os.path.exists("sector_model.pkl"):
        print("❌ sector_model.pkl not found!")
        print("   Run: python 2_train_model.py first")
        return

    # 2. Copy model to backend
    dest = "../backend/app/sector_model.pkl"
    shutil.copy("sector_model.pkl", dest)
    print(f"✅ Copied sector_model.pkl → backend/app/")

    # 3. Swap scorer files
    src_ml   = "../backend/app/scorer_ml.py"
    src_orig = "../backend/app/scorer.py"
    backup   = "../backend/app/scorer_formula_backup.py"

    if os.path.exists(src_ml):
        # Backup original formula scorer
        if os.path.exists(src_orig):
            shutil.copy(src_orig, backup)
            print(f"✅ Backed up original scorer → scorer_formula_backup.py")

        # Replace with ML scorer
        shutil.copy(src_ml, src_orig)
        print(f"✅ Swapped in ML scorer → scorer.py")
    else:
        print("❌ scorer_ml.py not found in backend/app/")
        return

    print("\n" + "=" * 50)
    print("🎉 Done! Now:")
    print("   1. git add .")
    print('   2. git commit -m "Add trained XGBoost model"')
    print("   3. git push")
    print("   4. Manual Deploy on Render")
    print("=" * 50)

if __name__ == "__main__":
    main()
