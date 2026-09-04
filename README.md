# Taxonomy Induction Pipeline

本项目从候选 terms 构建层次化 taxonomy。当前主流程不包含可选的 refinement 阶段。

## 流程总览

```text
Anthony terms
    |
    v
1. Semantic block partitioning
    |
    v
2. Recursive block-level taxonomy induction
    |
    v
3. Cross-block taxonomy fusion
    |
    v
4. LLM-guided global regrouping
    |
    v
regrouped_taxonomy.json
```

| 阶段 | 输入 | 主要操作 | 输出 |
| --- | --- | --- | --- |
| Block partition | 扁平 terms | Embedding、K-Means、选择分块数 | `clustered_terms_anthony.jsonl` |
| Block induction | 每个语义 block | Stage-G、Stage-A、递归细分 | `taxonomies_out_anthony/` |
| Fusion | 所有局部 taxonomies | 相似节点合并、父节点选择、标签统一 | `merged_taxonomy.json` |
| Regrouping | 融合后的 subtrees | 推断缺失的上位和中间概念，重建全局层次 | `regrouped_taxonomy.json` |

## 环境准备

```bash
cd /home/yirui/ourmethod

python3 -m pip install numpy scikit-learn sentence-transformers
export OPENAI_API_KEY="<your-openai-api-key>"
```

不要将真实 API key 写入脚本、README、日志或 Git commit。

## 示例数据

本文档只使用 Anthony terms：

```text
/home/yirui/ourmethod/anthony_words_list_deduplicated.json
```

建议统一设置以下路径变量：

```bash
TERMS_JSON=/home/yirui/ourmethod/anthony_words_list_deduplicated.json
CLUSTER_OUTPUT=/home/yirui/ourmethod/clustered_terms_anthony.jsonl
TAXONOMY_DIR=/home/yirui/ourmethod/taxonomies_out_anthony
MERGED_TAXONOMY="$TAXONOMY_DIR/merged_taxonomy.json"
REGROUPED_TAXONOMY="$TAXONOMY_DIR/regrouped_taxonomy.json"
```

## 1. Semantic block partitioning

首先将 terms 编码为语义向量，然后使用 K-Means 聚类。候选聚类数范围为：

$$
k^\star = \left\lceil \frac{|E|}{70} \right\rceil
$$

$$
\mathcal{K} =
\left[
\max\left(2, \left\lfloor 0.7k^\star \right\rfloor\right),
\min\left(k_{\mathrm{cap}}, \left\lceil 1.3k^\star \right\rceil\right)
\right].
$$

其中，$|E|$ 是 Anthony term 的数量，目标是让每个 block 平均包含约 70 个 terms。

当前的 `build_taxonomy_pipeline.py` 会执行分块并通过 `--cluster-output` 保存聚类结果，因此不需要再对同一数据单独运行一次 `block_partition.py`。

## 2. Recursive block-level taxonomy induction

对每个语义 block 执行：

1. **Stage-G (Generate)**：根据 terms 推断局部 category concepts。
2. **Stage-A (Assign)**：把 terms 分配到生成的 categories。
3. **Recursive expansion**：判断每个 category 是否需要继续执行 Stage-G 和 Stage-A。

阶段 1 和阶段 2 由以下命令连续完成：

```bash
python3 build_taxonomy_pipeline.py \
  --terms-json "$TERMS_JSON" \
  --cluster-output "$CLUSTER_OUTPUT" \
  --taxonomy-output-dir "$TAXONOMY_DIR" \
  --provider openai \
  --model gpt-4o-mini
```

预期产物：

```text
clustered_terms_anthony.jsonl
taxonomies_out_anthony/
├── block_01_taxonomy.json
├── block_02_taxonomy.json
└── ...
```

## 3. Cross-block taxonomy fusion

Fusion 将各个 block 的局部 taxonomies 合并成统一 taxonomy，主要包括：

- 根据 embedding 召回相似节点；
- 根据 `--merge-threshold` 判断是否合并；
- 使用 `--parent-top-k` 搜索合适的父节点；
- 使用 LLM 处理模糊的合并决策；
- 统一相近节点的标签风格。

```bash
python3 taxonomy_fusion.py \
  --input-dir "$TAXONOMY_DIR" \
  --output "$MERGED_TAXONOMY" \
  --merge-threshold 0.95 \
  --parent-top-k 5 \
  --use-llm \
  --llm-provider openai \
  --llm-model gpt-4o-mini \
  --harmonize-labels \
  --debug-merge
```

输出：

```text
/home/yirui/ourmethod/taxonomies_out_anthony/merged_taxonomy.json
```

较高的 `--merge-threshold` 更保守，可以降低语义相关但并非同义的节点被错误合并的概率。

## 4. LLM-guided global regrouping

Fusion 主要解决跨 block 的节点重复和挂载问题；regrouping 负责重新设计融合结果的全局层次。

`taxonomy_regrouper.py` 使用现有 subtree 的 label、description、relation、term count 和 child-label preview，执行：

1. 在 root 下推断新的上位类别；
2. 将现有 subtrees 分配到这些类别；
3. 检查未分配的 subtrees；
4. 当多个 leftovers 构成稳定主题时，补充缺失类别；
5. 递归推断必要的中间层；
6. 将仍无法可靠归类的内容放入 residual bucket。

因此，regrouping 是推断全局 missing concepts 和 intermediate concepts 的主要阶段。

```bash
python3 taxonomy_regrouper.py \
  "$MERGED_TAXONOMY" \
  --output "$REGROUPED_TAXONOMY" \
  --model gpt-4o-mini
```

最终结果：

```text
/home/yirui/ourmethod/taxonomies_out_anthony/regrouped_taxonomy.json
```

## 完整运行命令

```bash
cd /home/yirui/ourmethod

export OPENAI_API_KEY="<your-openai-api-key>"

TERMS_JSON=/home/yirui/ourmethod/anthony_words_list_deduplicated.json
CLUSTER_OUTPUT=/home/yirui/ourmethod/clustered_terms_anthony.jsonl
TAXONOMY_DIR=/home/yirui/ourmethod/taxonomies_out_anthony
MERGED_TAXONOMY="$TAXONOMY_DIR/merged_taxonomy.json"
REGROUPED_TAXONOMY="$TAXONOMY_DIR/regrouped_taxonomy.json"

python3 build_taxonomy_pipeline.py \
  --terms-json "$TERMS_JSON" \
  --cluster-output "$CLUSTER_OUTPUT" \
  --taxonomy-output-dir "$TAXONOMY_DIR" \
  --provider openai \
  --model gpt-4o-mini

python3 taxonomy_fusion.py \
  --input-dir "$TAXONOMY_DIR" \
  --output "$MERGED_TAXONOMY" \
  --merge-threshold 0.95 \
  --parent-top-k 5 \
  --use-llm \
  --llm-provider openai \
  --llm-model gpt-4o-mini \
  --harmonize-labels \
  --debug-merge

python3 taxonomy_regrouper.py \
  "$MERGED_TAXONOMY" \
  --output "$REGROUPED_TAXONOMY" \
  --model gpt-4o-mini
```

## 主要产物

| 文件或目录 | 含义 |
| --- | --- |
| `clustered_terms_anthony.jsonl` | Anthony terms 的语义分块结果 |
| `taxonomies_out_anthony/block_*_taxonomy.json` | 每个 block 的局部 taxonomy |
| `taxonomies_out_anthony/merged_taxonomy.json` | 跨 block 融合结果 |
| `taxonomies_out_anthony/regrouped_taxonomy.json` | 全局重组后的最终 taxonomy |

## 注意事项

- OpenAI 模型名是 `gpt-4o-mini`，中间没有空格。
- Shell 中的下划线不需要转义，例如写 `taxonomy_fusion.py`，不要保留 Markdown 中的 `\_`。
- 从富文本复制命令时，应检查并删除 non-breaking space 等不可见字符。
- `--input-dir` 必须只包含本次 Anthony 实验产生的 block taxonomies。
- `merge-threshold` 会显著影响最终粒度，应在实验记录中保存其取值。
