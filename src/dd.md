Can you tell when an LLM is lying from the activations? Are simple methods good enough? We recently published a [paper](https://arxiv.org/abs/2502.03407) investigating if linear probes detect when Llama is deceptive.

Abstract:

> AI models might use deceptive strategies as part of scheming or misaligned behaviour. Monitoring outputs alone is insufficient, since the AI might produce seemingly benign outputs while its internal reasoning is misaligned. We thus evaluate if linear probes can robustly detect deception by monitoring model activations. We test two probe-training datasets, one with contrasting instructions to be honest or deceptive (following [Zou et al., 2023](https://arxiv.org/abs/2310.01405)) and one of responses to simple roleplaying scenarios. We test whether these probes generalize to realistic settings where Llama-3.3-70B-Instruct behaves deceptively, such as concealing insider trading ([Scheurer et al., 2023](https://arxiv.org/abs/2311.07590)) and purposely underperforming on safety evaluations ([Benton et al., 2024](https://arxiv.org/abs/2410.21514)). We find that our probe distinguishes honest and deceptive responses with AUROCs between 0.96 and 0.999 on our evaluation datasets. If we set the decision threshold to have a 1% false positive rate on chat data not related to deception, our probe catches 95-99% of the deceptive responses. Overall we think white-box probes are promising for future monitoring systems, but current performance is insufficient as a robust defence against deception. Our probes' outputs can be viewed on our [website](http://data.apolloresearch.ai/dd/) and our code on [github](http://github.com/ApolloResearch/deception-detection).

We train probes using simple training data (from [RepE](https://arxiv.org/abs/2310.01405) paper) and techniques (logistic regression):

![](img/dd/1.webp)

We test these probes in more complicated and realistic environments where Llama-3.3-70B responds deceptively:

![](img/dd/2.webp)

The probe fires far less on alpaca responses unrelated to deception, indicating it may partially be a probe for “deception-related” text rather than “actually-deceptive” text.

We compare a variety of probing methods. Training on roleplaying scenarios and probing the activations after a follow-up question works well. Using SAE activations or the probe from [Simple Probes Can Catch Sleeper Agents](https://www.anthropic.com/research/probes-catch-sleeper-agents) works less well.

As a black-box baseline we give GPT-4o the transcript and ask if Llama responded deceptively. Our probe performs comparably to this baseline, although we iterated more on the probe than the baseline.

![](img/dd/3.webp)


While the probes are decent, they are imperfect. Some common failures:

- The probe firing on honest confessions of prior deception ([example 1](https://data.apolloresearch.ai/dd/instructed-pairs/roleplaying__plain/sample_347_honest.html))
- The mean score being incorrect even if the per-token probe behavior is reasonable ([example 2](https://data.apolloresearch.ai/dd/instructed-pairs/roleplaying__plain/sample_270_deceptive.html)).
- But other failures have no easy explanation, such as [example 3](https://data.apolloresearch.ai/dd/instructed-pairs/roleplaying__plain/sample_80_honest.html) below where the probe fires on an objectively-honest response.

![](img/dd/4.webp)

We are excited about future work improving deception-probes. We are especially curious to see if probes work in more difficult settings where it’s not obvious from the transcript that the model is being deceptive–for example environments where models [alignment fake](https://arxiv.org/abs/2412.14093) or [sandbag](https://arxiv.org/abs/2412.04984) even without chain-of-thought.

Find the full paper [here](https://arxiv.org/abs/2502.03407), our code [here](https://github.com/ApolloResearch/deception-detection), and our website displaying probe-outputs [here](https://data.apolloresearch.ai/dd/).