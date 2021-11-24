from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import collections as mcoll
import matplotlib
from string import ascii_uppercase, ascii_lowercase

from colabfold.colabfold import (
    pymol_color_list,
    pymol_cmap,
    alphabet_list,
    kabsch,
    plot_pseudo_3D,
    add_text,
    plot_ticks,
)


def plot_predicted_alignment_error(
    jobname: str, num_models: int, outs: dict, result_dir: Path, show: bool = False
):
    plt.figure(figsize=(3 * num_models, 2), dpi=100)
    for n, (model_name, value) in enumerate(outs.items()):
        plt.subplot(1, num_models, n + 1)
        plt.title(model_name)
        plt.imshow(value["pae"], label=model_name, cmap="bwr", vmin=0, vmax=30)
        plt.colorbar()
    plt.savefig(result_dir.joinpath(jobname + "_PAE.png"))
    if show:
        plt.show()
    plt.close()


def plot_lddt(
    jobname: str, msa, outs: dict, query_sequence, result_dir: Path, show: bool = False
):
    # gather MSA info
    seqid = (query_sequence == msa).mean(-1)
    seqid_sort = seqid.argsort()  # [::-1]
    non_gaps = (msa != 21).astype(float)
    non_gaps[non_gaps == 0] = np.nan

    plt.figure(figsize=(14, 4), dpi=100)

    plt.subplot(1, 2, 1)
    plt.title("Sequence coverage")
    plt.imshow(
        non_gaps[seqid_sort] * seqid[seqid_sort, None],
        interpolation="nearest",
        aspect="auto",
        cmap="rainbow_r",
        vmin=0,
        vmax=1,
        origin="lower",
    )
    plt.plot((msa != 21).sum(0), color="black")
    plt.xlim(-0.5, msa.shape[1] - 0.5)
    plt.ylim(-0.5, msa.shape[0] - 0.5)
    plt.colorbar(label="Sequence identity to query")
    plt.xlabel("Positions")
    plt.ylabel("Sequences")

    plt.subplot(1, 2, 2)
    plt.title("Predicted lDDT per position")
    for model_name, value in outs.items():
        plt.plot(value["plddt"], label=model_name)

    plt.legend()
    plt.ylim(0, 100)
    plt.ylabel("Predicted lDDT")
    plt.xlabel("Positions")
    plt.savefig(str(result_dir.joinpath(jobname + "_coverage_lDDT.png")))
    if show:
        plt.show()
    plt.close()

def plot_protein_confidence(
    plot_path,
    protein=None,
    pos=None,
    plddt=None,
    pae=None,
    Ls=None,
    dpi=200,
    best_view=True,
    line_w=2.0,
    show=False,
):

    use_ptm = pae is not None

    if protein is not None:
        pos = np.asarray(protein.atom_positions[:, 1, :])
        plddt = np.asarray(protein.b_factors[:, 0])

    # get best view
    if best_view:
        if plddt is not None:
            weights = plddt / 100
            pos = pos - (pos * weights[:, None]).sum(0, keepdims=True) / weights.sum()
            pos = pos @ kabsch(pos, pos, weights, return_v=True)
        else:
            pos = pos - pos.mean(0, keepdims=True)
            pos = pos @ kabsch(pos, pos, return_v=True)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(
        nrows=2, ncols=2, gridspec_kw={"height_ratios": [1.5, 1]}
    )
    fig.set_figwidth(7)
    fig.set_figheight(7)
    ax = {"prot_chain": ax1, "prot_plddt": ax2, "IDDT": ax3, "Ali_error": ax4}

    fig.set_dpi(dpi)
    fig.subplots_adjust(top=0.9, bottom=0.1, right=1, left=0.1, hspace=0, wspace=0.05)

    # 3D PLOT:
    xy_min = pos[..., :2].min() - line_w
    xy_max = pos[..., :2].max() + line_w
    for a in [ax["prot_chain"], ax["prot_plddt"]]:
        a.set_xlim(xy_min, xy_max)
        a.set_ylim(xy_min, xy_max)
        a.axis(False)

    if Ls is None or len(Ls) == 1:
        # color N->C
        c = np.arange(len(pos))[::-1]
        plot_pseudo_3D(pos, line_w=line_w, ax=ax1)
        add_text("colored by N→C", ax1)
    else:
        # color by chain
        c = np.concatenate([[n] * L for n, L in enumerate(Ls)])
        if len(Ls) > 40:
            plot_pseudo_3D(pos, c=c, line_w=line_w, ax=ax1)
        else:
            plot_pseudo_3D(
                pos, c=c, cmap=pymol_cmap, cmin=0, cmax=39, line_w=line_w, ax=ax1
            )
        add_text("colored by chain", ax1)

    if plddt is not None:
        # color by pLDDT
        plot_pseudo_3D(pos, c=plddt, cmin=50, cmax=90, line_w=line_w, ax=ax2)
        add_text("colored by pLDDT", ax2)

    # Conf plot:
    ax["IDDT"].set_title("Predicted lDDT")
    ax["IDDT"].plot(plddt)
    if Ls is not None:
        L_prev = 0
        for L_i in Ls[:-1]:
            L = L_prev + L_i
            L_prev += L_i
            ax["IDDT"].plot([L, L], [0, 100], color="black")
    ax["IDDT"].set_ylim(0, 100)
    ax["IDDT"].set_ylabel("plDDT")
    ax["IDDT"].set_xlabel("position")

    if use_ptm:
        ax["Ali_error"].set_title("Predicted Aligned Error")
        Ln = pae.shape[0]
        ax["Ali_error"].imshow(pae, cmap="bwr", vmin=0, vmax=30, extent=(0, Ln, Ln, 0))
        if Ls is not None and len(Ls) > 1:
            plot_ticks(Ls)
        # ax['Ali_error'].colorbar()
        ax["Ali_error"].set_xlabel("Scored residue")
        ax["Ali_error"].set_ylabel("Aligned residue")

    plt.savefig(plot_path)
    if show:
        plt.show()
    plt.close()
