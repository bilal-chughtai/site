**TL;DR:** There may be a fundamental problem with interpretability work that attempts to understand neural networks by decomposing their individual activation spaces in isolation: It seems likely to find _features of the activations_ - features that help explain the statistical structure of activation spaces, rather than _features of the model_ - the features the model’s own computations make use of.

_Written at Apollo Research_

# Introduction

**Claim: Activation space interpretability is likely to give us features of the activations, not features of the model, and this is a problem.**

Let’s walk through this claim.

**What do we mean by activation space interpretability?** Interpretability work that attempts to understand neural networks by explaining the inputs and outputs of their layers in isolation. In this post, we focus in particular on the problem of _decomposing_ activations, via techniques such as [sparse](https://arxiv.org/abs/2309.08600) [autoencoders](https://transformer-circuits.pub/2023/monosemantic-features) (SAEs), PCA, or just by looking at individual [neurons](https://openai.com/index/language-models-can-explain-neurons-in-language-models/). This is in contrast to interpretability work that leverages the wider functional structure of the model and incorporates more information about how the model performs computation. Examples of existing techniques using such information include [Transcoders](https://arxiv.org/abs/2406.11944), [end2end-SAEs](https://arxiv.org/abs/2405.12241) and [joint activation/gradient PCAs](https://arxiv.org/abs/2405.10928). 

**What do we mean by “features of the activations”?** Sets of features that help explain or make manifest the statistical structure of the model’s activations at particular layers. One way to try to operationalise this is to ask for decompositions of model activations at each layer that try to [minimise the description length of the activations in bits](https://www.lesswrong.com/posts/G2oyFQFTE5eGEas6m/interpretability-as-compression-reconsidering-sae).

**What do we mean by “features of the model”?** The set of features the model itself actually thinks in, the decomposition of activations along which its own computations are structured, features that are significant to what the model is _doing_ and how it is doing it. One way to try to operationalise this is to ask for the decomposition of model activations that makes the causal graph of the whole model as manifestly simple as possible: We make each feature a graph node, and draw edges indicating how upstream nodes are involved in computing downstream nodes. To understand the model, we want the decomposition that results in the most structured graph with the fewest edges, with meaningfully separate modules corresponding to circuits that do different things. 

Our claim is pretty abstract and general, so we’ll try to convey the intuition behind it with concrete and specific examples.

# Examples illustrating the general problem 

In the following, we will often use SAEs as a stand-in for any technique that decomposes individual activation spaces into sets of features. But we think the problems these examples are trying to point to apply in some form to basically any technique that tries to decompose individual activation spaces in isolation.

**1. Activations can contain structure of the data distribution that the models themselves don’t ‘know’ about.**  

Consider a simple model that takes in a two-dimensional input $(x, y)$ and computes some scalar function of the two, $f(x,y)$. Suppose for all data points in the data distribution, the input data $(x, y)$ falls on a very complicated one-dimensional curve. Also, suppose that the trained model is blind to this fact and treats the two input variables as entirely independent (i.e. none of the model’s computations make use of the relationship between $x$ and $y$. If we were to study the activations of this model, we might notice this curve (or transformed curve) and think it meaningful. 

In general, data distributions used for training (and often also interpreting) neural networks contain a very large amount of information about the process that _created_ said dataset. For all non-toy data distributions, the distribution will reflect complex statistical relationships of the universe. A model with finite capacity can't possibly learn to make use of all of these relationships. Since activations are just mathematical transformations of inputs sampled from this data distribution, by studying neural networks through their distribution of activations, we should expect to see many of those unused relationships in the activations. So, fully understanding the model’s activations can in a sense be substantially _harder_ than fully understanding what the model is doing. And if we don’t look at the computations the model is carrying out on those activations _before_ we try to decompose them, we might struggle to tease apart properties of the input distribution and properties of the model.

**2. The learned feature dictionary may not match the “model’s feature dictionary”.**

Now let’s consider another one-dimensional curve, this time embedded in a ten-dimensional space. One of the nice things about sparse dictionary methods like SAEs is that they can approximate curves like this pretty well, using a large dictionary of features with sparse activation coefficients. If we train an SAE with a dictionary of size 500 on this manifold, we might find 500 features, only a very small number of which are active at a time, corresponding to different tiny segments of the curve.

Suppose, however, that the model _actually_ thinks of this single dense data-feature as a sparse set of $100$ linear directions. We term this set of directions the “_model’s dictionary”._ The model’s dictionary approximates most segments of the curve with lower resolution than our dictionary, but it might approximate some crucial segments a lot more finely. MLPs and attention heads downstream in the model carry out computations on these 100 sparsely activating directions. The model’s decomposition of the ten-dimensional space into 100 sparse features and our decomposition of the space into 500 sparse features are necessarily quite different. Some features and activation coefficients in the two dictionaries _might_ be closely related, but we should not expect most to be. If we are not looking at what the model _does_ with these activations downstream, how can we tell that the feature dictionary we find matches the model’s feature dictionary? When we perform the decomposition, we don’t know yet what parts of the curve are more important for what the model is computing downstream, and thus how the model is going to think about and decompose the ten-dimensional subspace. We probably won’t even be aware in the first place that the activations we are decomposing lie on a one-dimensional curve without significant [extra work](https://arxiv.org/abs/2405.14860). 

**3. Activation space interpretability can fail to find compositional structure.** 

Suppose our model represents four types of object in some activation space: {blue square, red square, blue circle, red circle}. We can think of this as the direct product space {blue, red} $\otimes$ {square, circle}. Suppose the model’s 'true features' are colour and shape, in the sense that later layers of the model read the 'colour' variable and the 'shape' variable independently.  Now, suppose we train an SAE with 4 dictionary elements on this space. SAEs are optimised to achieve high sparsity -- few latents should be active on each forward pass. An SAE trained on this space will therefore learn the four latents {blue square, red square, blue circle, red circle} (the "composed representation"), rather than {blue, red} $\otimes$ {square, circle} (the "product representation"), as the former has sparsity 1, while the latter has sparsity 2. In other words, the SAE learns [features](https://www.lesswrong.com/posts/QoR8noAB3Mp2KBA4B/do-sparse-autoencoders-find-true-features) [that](https://www.lesswrong.com/posts/a5wwqza2cY3W7L9cj/sparse-autoencoders-find-composed-features-in-small-toy) [are](https://www.lesswrong.com/posts/tojtPCCRpKLSHBdpn/the-strong-feature-hypothesis-could-be-wrong) [compositions](https://arxiv.org/abs/2407.14662) of the model’s features. 

Can we fix this by adjusting the sparsity penalty? Probably not. Any sparse-dictionary approach set to decompose the space as a whole will likely learn this same set of four latents, as this latent set is sparser, with [shorter description length](https://arxiv.org/abs/2410.11179) than the product set. 

While we _could_ create some ansatz for our dictionary learning approach that specifically privileges the product configuration, this is cheating. How would we know the product configuration and not the composed configuration matches the structure of the model’s downstream computations in this case in advance, if we only look at the activations in isolation? And even if we do somehow know the product configuration is right, how would we know in advance to look for this specific 2x2 structure? In reality, it would additionally be embedded in a larger activation space with an unknown number of further latents flying around besides just shape and colour. 

**4: Function approximation creates artefacts that activation space interpretability may fail to distinguish from features of the model.**

This one is a little more technical, so we’ll take it in two stages. First, a very simplified version, then something that’s closer to the real deal.

**Example 4a: Approximating** $x^2$_._ Suppose we have an MLP layer that takes a scalar input $x$ and is trained to approximate the scalar output $x^2$. The MLP comprises a $\text{W}_{in}$ matrix (vector, really) of shape $(1, 10)$ that maps $x$ to some pre-activation. This gets mapped through a ReLU, giving a $10$ dimensional activation vector $a$. Finally, these are mapped to a scalar output via some $\text{W}_{out}$ matrix of shape $(10, 1)$. Thus, concretely, this model is tasked with approximating $x^2$ via a linear combination of ten functions of the form $\text{ReLU}(ax+b)$. Importantly, the network only cares about one direction in the 10 dimensional activation space, the one which gives a good approximation of $x^2$ and is projected off by $\text{W}_{out}$. There are 9 other orthogonal directions in the hidden space. Unless we know in advance that the network is trying to compute $x^2$, this important direction will not stick out to us. If we train an SAE on the hidden activations, or do a PCA, or perform any other activation decomposition of our choice, we will get out a bunch of directions, and likely none of them will be $x^2$. What makes the $x^2$ direction special is that the model uses it downstream (which, here, means that this direction is special in $\text{W}_{out}$). But that information can't be found in the hidden activations alone. We need more information. 

**Example 4b: Circuits in superposition**. The obvious objection to Example 4a is that $\text{W}_{out}$ is natively a rank one matrix, so the fact that only one direction in the 10 dimensional activation space matters is trivial and obvious to the researcher. So while we do need to use some information that isn’t in the activations, it’s a pretty straightforward thing to find. But if we extend the above example to something more realistic, it’s not so easy anymore. Suppose the model is computing a bunch of the above multi-dimensional [circuits in superposition](https://www.lesswrong.com/posts/roE7SHjFWEoMcGZKd/circuits-in-superposition-compressing-many-small-neural). For example, take an MLP layer instead with 40,000 neurons, computing 80,000 functions of (sparse) scalar inputs, each of which requires 10 neurons to compute, and writes the results to a 10,000 dimensional residual stream. Each of these 80,000 circuits would then occupy some ten-dimensional subspace in the 40,000 dimensional activation space of the MLP, meaning the subspaces must overlap. Each of these subspaces may only have one direction that actually matters for downstream computation. 

Our SAE/PCA/activation-decomposition-of-choice trained on the activation space will not be able to tell which directions are actually used by the model, and which are an artefact of computing the directions that do matter. They will decompose these ten-dimensional subspaces into a bunch of directions, which almost surely won’t line up with the important ones. To make matters worse, we might not immediately know that something went wrong with our decomposition. All of these directions might look like they relate to some particular subtask when studied through the lens of e.g. max activating dataset examples, since they’ll cluster along the circuit subspaces to some extent. So the decomposition could actually look very interesting and interpretable, with a lot of directions that appear to somewhat-but-not-quite make sense when we study them. However, these many directions will seem to interact with the next layer in a very complicated manner.

# The general problem 

Not all the structure of the activation spaces matters for the model’s computations, and not all the structure of the model’s computations is manifest in the structure of individual activation spaces. 

So, if we are trying to understand the model by _first_ decomposing its activation spaces into features and _then_ looking at how these features interact and form circuits, we might get a complete mess of interactions that do not make the structure of the model and what it is doing manifest at all. We need to have at least some relevant information about how the model itself uses the activations _before_ we pick our features, and include that information in the activation space decomposition. Even if our goal is just to understand an aspect of the model’s representation enough for a use case like monitoring, looking at the structure of the activation spaces rather than the structure of the model’s computations can give us features that don’t have a clean causal relationship to the model’s structure and which thus might mislead us. 

# What can we do about this?

If the problem is that our decomposition methodologies lack relevant information about the network, then maybe the solution is giving them more of it. How could we try to do this?

**Guess the correct** [**ansatz**](https://en.wikipedia.org/wiki/Ansatz)**.** We can try to make a better ansatz for our decompositions by guessing in advance how model computations are structured. This requires progress on interpretability fundamentals, through e.g. understanding the structure and purpose of [feature geometry](https://www.lesswrong.com/posts/MFBTjb2qf3ziWmzz6/sae-feature-geometry-is-outside-the-superposition-hypothesis) better. Note however that the current favoured roadmap for making progress on those topics seems to be “decompose the activations well, understand the resulting circuits and structure, and then hope this yields increased understanding”. This may be a bit of a chicken-and-egg situation. 

**Use activations (or gradients) from more layers.** We can try to use information from more layers to look for decompositions that simplify the model as a whole. For example, we can decompose multiple layers simultaneously and impose a sparsity penalty on connections between features in different layers. Other approaches that fall vaguely in this category include [end-to-end-SAEs,](https://arxiv.org/pdf/2405.12241) [Attribution Dictionary Learning,](https://transformer-circuits.pub/2024/april-update/index.html#attr-dl) [Transcoders](https://arxiv.org/abs/2406.11944), and [Crosscoders](https://transformer-circuits.pub/2024/crosscoders/index.html).

**Use weights instead of or to supplement activations.** Most interpretability work studies activations and not weights. There are good reasons for this: activations are lower dimensional than weights. The curse of dimensionality is real. However, weights, in a sense, contain the entire functional structure of the model, because they _are_ the model. It seems in principle possible to decompose weights into circuits _directly_, by minimising some complexity measure over some kind of weight partitioning, without any intermediary step of decomposing activations into features at all. This would be a reversal of the standard, activations-first approach, which aims to understand features first and later understand the circuits. Apollo Research are currently trying this.

_Thanks to Andy Arditi, Dan Braun, Stefan Heimersheim and Lee Sharkey for feedback._