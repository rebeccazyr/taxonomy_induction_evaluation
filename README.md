# Taxonomy Induction Evaluation

本仓库用于从候选概念（terms/entities）构建层次化 taxonomy，并与 Chain-of-Layer（CoL）等方法进行比较。

本文档记录当前使用的 taxonomy 构建主流程。这里不包含可选的 refinement 阶段。

## 方法总览

```text
Candidate terms/entities
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
Final taxonomy
```

四个阶段的职责不同：

| 阶段 | 输入 | 主要操作 | 输出 |
| --- | --- | --- | --- |
| Block partition | 扁平 terms/entities | Embedding、K-Means、选择分块数 | `*.jsonl` clusters |
| Block taxonomy induction | 每个语义 block | Stage-G 生成类别、Stage-A 分配 terms、递归细分 | 每个 block 的局部 taxonomy |
| Taxonomy fusion | 所有局部 taxonomies | 相似节点召回、合并、父节点选择、标签统一 | `merged_taxonomy.json` |
| Taxonomy regrouping | 融合后的 subtrees | 推断缺失的上位/中间概念，重新组织全局层次 | `regrouped_taxonomy.json` |

## 1. 环境准备

```bash
python3 -m pip install numpy scikit-learn sentence-transformers
export OPENAI_API_KEY="<your-openai-api-key>"
```

不要将真实 API key 写进脚本、README、日志或 Git commit。

## 2. Semantic block partitioning

首先将候选 terms/entities 编码为向量，然后进行 K-Means 聚类。候选聚类数范围为：

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

其中，$|E|$ 是输入 entity/term 数量，目标是让每个 block 平均包含约 70 个实体。

### MAG-CS 示例

```bash
INPUT_JSON=/home/yirui/taxonomy_induction_evaluation/dataset/generated/MAG_cs/K_axis_S2k/final/mag_cs_KaxisS2k_2000_v1_mask0p25/test.json
CLUSTERED_JSONL=/home/yirui/ourmethod/cs_2000_mask0_clustered.jsonl

python3 block_partition.py \
  --input "$INPUT_JSON" \
  --output "$CLUSTERED_JSONL"
```

### EMNLP 2022 terms 示例

```bash
python3 block_partition.py \
  --input /home/yirui/ourmethod/terms_method_combined_2022.json \
  --output /home/yirui/ourmethod/terms_method_combined_2022_clustered.jsonl
```

独立运行 `block_partition.py` 适合检查聚类结果，或为 CoL 等其他方法准备 clustered input。如果使用下一节的 `build_taxonomy_pipeline.py`，其 `--cluster-output` 会保存构建过程中产生的 cluster 文件，无需对同一份数据重复执行分块。

## 3. Recursive block-level taxonomy induction

`build_taxonomy_pipeline.py` 对每个 block 构建局部 taxonomy：

1. **Stage-G (Generate)**：根据 block 中的 terms 推断局部 category concepts。
2. **Stage-A (Assign)**：把 terms 分配到生成的 categories。
3. **Recursive expansion**：判断每个 category 是否需要继续执行 Stage-G/Stage-A。

### EMNLP 2022

```bash
python3 build_taxonomy_pipeline.py \
  --terms-json /home/yirui/ourmethod/terms_method_combined_2022.json \
  --cluster-output /home/yirui/ourmethod/clustered_terms_2022.jsonl \
  --taxonomy-output-dir /home/yirui/ourmethod/taxonomies_out_2022 \
  --provider openai \
  --model gpt-4o-mini
```

### Anthony terms

```bash
python3 build_taxonomy_pipeline.py \
  --terms-json /home/yirui/ourmethod/anthony_words_list_deduplicated.json \
  --cluster-output /home/yirui/ourmethod/clustered_terms_anthony.jsonl \
  --taxonomy-output-dir /home/yirui/ourmethod/taxonomies_out_anthony \
  --provider openai \
  --model gpt-4o-mini
```

### EMNLP 2024

```bash
python3 build_taxonomy_pipeline.py \
  --terms-json /home/yirui/ourmethod/terms_method_combined_2024.json \
  --cluster-output /home/yirui/ourmethod/clustered_terms_2024.jsonl \
  --taxonomy-output-dir /home/yirui/ourmethod/taxonomies_out_2024 \
  --provider openai \
  --model gpt-4o-mini
```

## 4. Cross-block taxonomy fusion

Fusion 将各个 block 的局部 taxonomies 合并成统一 taxonomy。主要操作包括：

- 根据 embedding 召回相似节点；
- 根据 `--merge-threshold` 决定是否合并；
- 使用 `--parent-top-k` 搜索合适的父节点；
- 可选地让 LLM 处理模糊合并；
- 可选地统一相近节点的标签风格。

### EMNLP 2024：embedding-based fusion

```bash
python3 taxonomy_fusion.py \
  --input-dir /home/yirui/ourmethod/taxonomies_out_2024 \
  --output /home/yirui/ourmethod/taxonomies_out_2024/merged_taxonomy.json \
  --batch-size 16 \
  --merge-threshold 0.85 \
  --device cpu \
  --parent-top-k 5
```

### Anthony：embedding + LLM fusion

```bash
python3 taxonomy_fusion.py \
  --input-dir /home/yirui/ourmethod/taxonomies_out_anthony \
  --output /home/yirui/ourmethod/taxonomies_out_anthony/merged_taxonomy.json \
  --merge-threshold 0.95 \
  --parent-top-k 5 \
  --use-llm \
  --llm-provider openai \
  --llm-model gpt-4o-mini \
  --harmonize-labels \
  --debug-merge
```

较高的 `--merge-threshold` 更保守，可降低语义相关但并非同义的节点被错误合并的概率。

## 5. LLM-guided global regrouping

Fusion 主要解决跨 block 的重复和挂载问题；regrouping 则重新设计融合结果的全局层次。

`taxonomy_regrouper.py` 使用现有 subtree 的 label、description、relation、term count 和 child-label preview：

1. 在指定 root 下推断新的上位类别；
2. 将现有 subtrees 分配到这些类别；
3. 检查 unassigned subtrees；
4. 当多个 leftovers 形成稳定主题时，补充缺失类别；
5. 递归推断必要的中间层；
6. 将仍无法可靠归类的内容放入 residual bucket。

因此，regrouping 是本方法中推断全局 missing concepts / intermediate concepts 的主要阶段。

### Anthony 示例

```bash
python3 taxonomy_regrouper.py \
  /home/yirui/ourmethod/taxonomies_out_anthony/merged_taxonomy.json \
  --output /home/yirui/ourmethod/taxonomies_out_anthony/regrouped_taxonomy.json \
  --model gpt-4o-mini
```

## 6. 推荐的完整运行顺序

以下命令展示一条不包含 refinement 的完整 Anthony pipeline：

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

最终结果为：

```text
/home/yirui/ourmethod/taxonomies_out_anthony/regrouped_taxonomy.json
```

## Chain-of-Layer baseline

CoL 是单独的 baseline，不属于上述四阶段方法。其输入可以复用 block partition 的输出：

```bash
CLUSTERED_JSONL=/home/yirui/ourmethod/cs_2000_mask0_clustered.jsonl

/home/yirui/ourmethod/Chain-of-Layer/scripts/run_CoL.sh \
  "$CLUSTERED_JSONL" \
  --dataset mag_cs \
  --no-demos
```

实验记录中应分别报告：

```text
CoL baseline:
test.json -> block_partition.py -> run_CoL.sh

Our method:
terms JSON -> block-level induction -> fusion -> regrouping
```

## 主要产物

| 文件或目录 | 含义 |
| --- | --- |
| `clustered_terms_*.jsonl` | 语义分块结果 |
| `taxonomies_out_*/` | 每个 block 的局部 taxonomy |
| `merged_taxonomy.json` | 跨 block 融合结果 |
| `regrouped_taxonomy.json` | 全局重组后的最终 taxonomy |

## 注意事项

- OpenAI 模型名是 `gpt-4o-mini`，中间没有空格。
- Shell 中的下划线不需要转义，例如写 `taxonomy_fusion.py`，不要保留 Markdown 中的 `\_`。
- 从富文本复制命令时，应检查并删除 non-breaking space 等不可见字符。
- `--input-dir` 必须指向本次实验实际生成的 taxonomy 目录。
- 不同数据集应使用不同输出目录，避免 fusion 把其他实验的 block 文件一起读入。
- `merge-threshold` 会显著影响最终粒度，比较实验时应记录其取值。
