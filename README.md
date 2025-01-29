# A Simple Line Bot with Azure OpenAI


キーワード

１．"今日のラッキー牌", "麻雀占い", "占い"と入力すると、今日のマージャンやるときのラッキー牌を出力。

2.上がった１４枚の手牌の点数を計算できる、しかも符と役の計算もしめす。

英語キーボードで入力してください！！！

このように入力する      点数計算 123m22234555p456s,5p,(456s){222p},1m1m3s,7 14

第一部分は　上がった１４枚の手牌

第二部分は　どの牌であがた

第三部分は　仕掛けての部分、ないなら、ここでspaceしてください。  ()[]{}::　それぞれの符号はチー、ポン、明槓、暗槓を表示する。

第四部分は　どら表示牌　間隔なし　ないなら、ここでspaceしてください。

第五部分は　オプションです　数字を選んでください。下にご覧　　　数字間はspaceで入力


config = {
    1: "is_riichi",
    2: "player_wind=EAST",
    3: "player_wind=SOUTH",
    4: "player_wind=WEST",
    5: "player_wind=NORTH",
    6: "round_wind=EAST",
    7: "round_wind=SOUTH",
    8: "round_wind=WEST",
    9: "round_wind=NORTH",
    10: "is_ippatsu",
    11: "is_rinshan",
    12: "is_chankan",
    13: "is_haitei",
    14: "is_houtei",
    15: "is_daburu_riichi",
    16: "is_nagashi_mangan",
    17: "is_tenhou",
    18: "is_renhou",
    19: "is_chiihou"
}
