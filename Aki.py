import akinator

def test_akinator():
    aki = akinator.Akinator()
    aki.start_game()

    while aki.progression <= 80:
        print(f"\nسوال: {aki.question}")
        ans = input("جواب ([y]es/[n]o/[i] don't know/[p]robably/[pn] probably not/[b]ack): ").strip().lower()

        if ans == "b":
            try:
                aki.back()
            except akinator.CantGoBackAnyFurther:
                print("نمیشه عقب رفت!")
            continue

        try:
            aki.answer(ans)
        except akinator.InvalidChoiceError:
            print("جواب نامعتبر، دوباره تلاش کن.")
            continue

    print(f"\n--- نتیجه ---")
    print(f"حدس: {aki.name_proposition}")
    print(f"توضیح: {aki.description_proposition}")
    print(f"عکس: {aki.photo}")

if __name__ == "__main__":
    test_akinator()
