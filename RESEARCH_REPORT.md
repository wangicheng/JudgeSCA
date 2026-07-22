# JudgeSCA: 側寫通道評估框架研究報告

## 摘要

* **問題:** 自動化評測系統 (Online Judge, OJ) 的受限沙盒常忽略系統回傳的硬體遙測數據可能成為資料外洩的隱蔽途徑。
* **方法:** 本研究 (JudgeSCA) 實證即使在無網路、無檔案系統讀取權限的黑盒沙盒中，仍可將隱藏測資編碼至記憶體開銷。結合字典樹 (Trie) 的深度優先搜尋 (DFS) 與 LCP 回溯機制，成功實現 $O(N)$ 複雜度的多筆測資並行解構。
* **成果與防禦:** 隱蔽通道 (Covert Channel) 吞吐量達 0.82 Bytes/sec，位元錯誤率 (BER) 為 0%。本研究亦分析了「粗粒度量化」與「差分隱私雜訊」防禦，並提供極低工程成本的 C 語言系統修補方案。

## 1. 研究背景與威脅模型

自動化評測系統通常將程式碼運行於受限沙盒（Docker / seccomp）。然而，本研究揭露攻擊者可利用 Web 前端回傳的 **`memory_cost` 遙測指標**建立高頻寬隱蔽通道，竊取未公開的測試資料。

### 1.1 威脅模型假設

* **權限限制：** 僅具備普通參賽者權限，無 Root 權限，無法修改沙盒配置或逃逸至宿主機。
* **環境隔離：** 無外網連線能力（無法使用 Socket/HTTP），檔案系統唯讀或隔離。
* **可得資訊：** 僅能讀取前端公開之遙測數據（`memory_cost`）與基本狀態（AC/WA/TLE）。

### 1.2 核心技術與防禦對抗

本研究整合了底層系統、演算法設計與資料科學等跨領域技術：

1. **精準記憶體控制與優化對抗:** 透過動態記憶體分配機制，將隱藏資料精確編碼為記憶體開銷。以 C++ 實作為例，我們透過動態邊界存取與 `volatile` 變數綁定，成功防止了 `-O2` 級別的死碼消除，確保訊號發射的絕對確定性。
2. **基於字典樹遍歷的多測資解構演算法:** 針對 OJ 僅回傳多測試點「最大記憶體值」的特性，我們可將所有測資視為一棵字典樹 (Trie)，並利用此特性依字典序由大至小進行 DFS 遍歷。當抵達葉節點 (完整測資) 時，再透過查詢 LCP (最長共同前綴) 快速回溯至上一個分岔點，藉此以 $O(N)$ 複雜度完整重建所有測資。
3. **線性迴歸建模:** 將 ASCII 數值與記憶體開銷建立線性映射，利用統計模型消除沙盒環境的基礎記憶體雜訊。

> [!NOTE]
> **倫理聲明：** 所有實證均於 **本地隔離沙盒（QDUOJ Docker）** 中進行，測資已徹底匿名化，絕未探測或干擾任何線上生產系統。

## 2. 實證數據統計與視覺化

所有數據採樣均於真實 QDUOJ 沙盒環境下透過軌跡驅動模擬完成。

### 2.1 實驗 1：測量精準度與線性關係

* **理論容量**：單次提交頻寬上限 $C = \log_2 \left( \lfloor \frac{M_{\text{limit}} - M_{\text{base}}}{\Delta} \rfloor \right)$。在 512MB 限制下， $C \approx 8\text{ bits/submission}$ （可攜帶 1 個 ASCII 字元）。
* **實測數據**：
  * **決定係數 ($R^2$)**: **1.0000** ($y = 1.0001x + 2.8285$)
  * **環境雜訊**: 僅 **0.0619 MB**
* **結論**：極致的 $R^2$ 證明此側寫通道具備絕對的物理確定性。*(參見 `figure1_staircase.pdf`)*

### 2.2 實驗 2：傳輸吞吐量與位元錯誤率

* **實測吞吐量 (目標字串 `hello, world!\n`)**：
  * **0.0s 延遲**: **0.82 Bytes/sec** | BER: **0.0%**
  * **1.0s 延遲**: **0.45 Bytes/sec** | BER: **0.0%**
  * **2.0s 延遲**: **0.31 Bytes/sec** | BER: **0.0%**
* **結論**：即便加入 2.0 秒延遲以規避 WAF 限速，隱蔽通道依然保持 100% 正確率。*(參見 `figure2_tradeoff.pdf`)*

### 2.3 實驗 3：多筆測資並行解構

* **提取原理**: 將未知的 ASCII 字元編碼為記憶體分配量，利用 OJ 會回傳多筆測資中「最大記憶體消耗」的特性，直接且精準地漏出字典序最大的字元，**完全無須進行字母表掃描**。
* **總提交次數與數學複雜度**: 僅需 **48 次**提交即可完整萃取出所有 7 筆測資（總字元 $N=39$）。數學複雜度上界嚴格收斂於 $S_{\text{total}} \le N + 2K$。這在數學上證明了此字典樹 DFS 解構演算法為 $O(N)$，徹底超越了傳統盲測必須的 $O(N \cdot |\Sigma|)$ 複雜度。
    * <i>(註：雖然當 LCP 長度 $\ge 32$ 時，Base-32 的 LCP 萃取會需要 $2$ 次以上的提交，但這代表同時省去了至少 $32$ 次的字元萃取提交。透過均攤分析，額外的 LCP 探測成本會被省下的字元探測成本完美抵銷，因此 $N+2K$ 的上界依然絕對成立。)</i>
* **解碼成功率**: **100%**

### 2.4 $O(N)$ 解構演算法虛擬碼

以下是本研究概念驗證 (PoC) 中所使用的多測資解構演算法。在概念上，我們可以將所有未知的測資集合想像成一棵字典樹 (Trie)。此演算法巧妙利用 OJ 會回傳多測試點「最大記憶體消耗」的特性，讓我們能依字典序由大至小對這棵樹進行深度優先搜尋 (DFS)。當遍歷到葉節點時，再利用查詢 LCP 來快速回溯到上一個分岔點，從而在 $O(N)$ 複雜度內完整走訪並重建出所有測資，完全無須對字母表進行掃描。

```python
def extract_testcases(M):
    """
    M: Maximum memory telemetry function (Submission to OJ)
    Returns: Array of extracted testcase strings T
    """
    T = []
    
    def extract_max_char(prefix, upper_bound):
        # 1. 產生載荷：若輸入匹配 prefix 且下一字元 < upper_bound，配置該字元 ASCII 值的記憶體
        payload = generate_cxx_payload(prefix, upper_bound)
        # 2. 提交至 OJ 並取得 memory_cost 最大值
        cost = M(payload)
        # 3. 透過線性迴歸模型反向解碼 ASCII
        val = decode_ascii(cost)
        return chr(val) if val >= 0 else None

    def extract_lcp(prefix):
        # 1. 產生載荷：找出與 prefix 的 LCP 長度並編碼為記憶體配置
        payload = generate_lcp_payload(prefix)
        cost = M(payload)
        return decode_lcp_length(cost)

    # Step 1: 萃取出字典序最大的第一筆測資
    P = ""
    while True:
        c = extract_max_char(prefix=P, upper_bound=INFINITY)
        if c is None: break
        P += c
    T.append(P)
    
    # Step 2: 迭代尋找字典序次小的測資，直到完全萃取
    while True:
        last_tc = T[-1]
        lcp_len = extract_lcp(last_tc)
        
        # 結束條件：找不到 LCP，或 LCP=0 且上一筆測資為空
        if lcp_len < 0 or (lcp_len == 0 and last_tc == ""):
            break
            
        P = last_tc[:lcp_len]
        upper_bound = last_tc[lcp_len]
        
        # 從分支點繼續萃取剩餘字元
        while True:
            c = extract_max_char(prefix=P, upper_bound=upper_bound)
            if c is None: break
            P += c
            # 分支點過後，後續字元不再受限
            upper_bound = INFINITY  
            
        T.append(P)
        
    return T
```

**演算法核心機制說明**：
1. **無掃描字元萃取**: 傳統的側寫通道可能需要逐一猜測字母表中的每一個字元。但本演算法的 `extract_max_char` 透過測試載荷直接將字元的 ASCII 值映射為記憶體配置量。由於 OJ 在多筆測資環境下會回傳所有測試點中的最大記憶體消耗，我們能透過單次提交，直接取得所有匹配前綴的測資中**字典序最大的字元**。
2. **LCP 快速回溯**: 當完整萃取出一筆測資 (抵達葉節點) 後，我們利用 `extract_lcp` 找出它與下一筆測資的最長公共前綴長度，藉此瞬間回溯到字典樹的上一個分岔點。
3. **上界約束 (DFS 遍歷)**: 在回溯到分岔點並繼續萃取時，我們將上一筆測資在該位置的字元設為 `upper_bound`，強迫載荷只回傳小於該字元的最大字元，藉此在字典樹上精準切換到下一條分支，確保 $K$ 筆測資能依字典序遞減的方向被完整 DFS 遍歷。

## 3. 防禦機制與對比實驗

### 3.1 防禦策略與對比

1. **粗粒度量化對齊:** 將系統回傳值對齊至 16MB 區塊。殘差標準差放大至 **4.6587 MB**，有效破壞高傳輸率下的記憶體解析度，迫使攻擊者必須大幅降低傳輸效率（例如降級為 Base-16 等）以維持通道穩定。
2. **動態雜訊注入:** 注入高斯雜訊（ $\sigma = 256\text{ KB}$ ）。雜訊標準差升至 **0.2388 MB**，需將 $\sigma$ 提高至 2MB 以上方能完整防堵。

### 3.2 系統實用性權衡

| 防禦策略 | 安全性 | 對一般用戶/學生的影響 |
| :--- | :--- | :--- |
| **16MB 粗粒度對齊** | 迫使攻擊者大幅降低傳輸效率 | 無法精準觀察微幅記憶體優化（如 3MB 與 15MB 皆顯示 16MB）。 |
| **高斯雜訊注入 ($\sigma=2\text{MB}$)** | 破壞 $R^2$ 擬合 | Memory 數據隨機波動；臨近記憶體邊界時可能導致誤判 (MLE)。 |

### 3.3 實務修補程式碼

粗粒度量化具備極低工程負擔。維護者僅需於 QDUOJ 之 C 語言 Judger 核心加入單行位元運算即可完成部署：

```c
// 將記憶體消耗對齊至 16MB (16777216 Bytes = 0x1000000) 之倍數
result->memory = ((result->memory + 0xFFFFFF) >> 24) << 24;
```

## 4. 研究限制

1. **前端資訊降級：** 若平台完全關閉 `memory_cost` 顯示，通道需降級為 1-bit/2-bit 狀態傳輸（觸發 TLE/MLE），傳輸速率將顯著下降。
2. **記憶體分配失敗限制：** 若單次要求配置的記憶體過大（例如超過 512MB），會因作業系統或容器分配失敗而直接引發 Runtime Error，導致無法獲得記憶體遙測數據。這為攻擊者放大量化步長設定了硬性的物理天花板。

## 5. 結論

本研究 (JudgeSCA) 實證了 OJ 系統中遙測數據帶來的資訊外洩風險，並提出 $O(N)$ 複雜度的字典樹 DFS 多測資解構演算法。同時，本研究評估並驗證了 16MB 粗粒度量化防禦方案，證明其能在極低工程代價下實現安全性與平台實用性的平衡。

## 6. 專案架構與實驗重現指南

為了完美符合資訊安全研究的「可重現性」標準，本專案提供了一鍵執行的 PoC 與數據視覺化模組。

### 6.1 專案目錄架構

```text
JudgeSCA/
├── poc/                    # 測試載荷與解構演算法核心
│   ├── main.py             # 概念驗證 (PoC) 主程式
│   ├── extractor.py        # 字典樹 DFS 與 LCP 回溯萃取邏輯
│   └── payload.py          # C++ 記憶體分配與 Anti-DCE 模板
├── analytics/              # 遙測數據分析與視覺化
│   ├── data/               # 實驗採集之真實遙測數據 (.csv)
│   ├── data_collector.py   # 自動化數據採樣腳本
│   └── visualize.py        # 生成 PDF 向量圖表
├── tmp/testcases/          # 本地測試用的真實測資集 (K=7, N=39)
└── RESEARCH_REPORT.md      # 本學術研究報告
```

### 6.2 實驗變數對照表

| 模組 | 命令列參數 | 說明 |
| :--- | :--- | :--- |
| **概念驗證執行 (`poc`)** | `--url <URL> --user <U> --password <P> --problem <ID>` | 執行自動化多測資解構。支援自訂目標 OJ 與題目 ID。 |
| **數據採樣 (`analytics`)** | `--iter <N> --delay <S>` | 調整實驗採樣次數與模擬 WAF 網路延遲，以重新產生 `data/` 目錄下的基礎觀測資料。 |

### 6.3 自動化實驗重現指令

```bash
# 1. 執行端到端多筆測資解構概念驗證 (O(N) 複雜度)
uv run python poc/main.py --url http://localhost:80 --user root --password rootroot --problem 1

# 2. 自動生成學術 PDF 向量圖表
uv run python analytics/visualize.py
```
