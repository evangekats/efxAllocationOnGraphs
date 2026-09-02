"""
allocationEFX.py
----------------
Υλοποίηση αλγορίθμου κατανομής σε γράφους με στόχο EFX (Envy-Free up to any good).
Το αρχείο περιλαμβάνει:
  • Greedy allocation (αρχική απόδοση αγαθών)
  • Reduce envy (προσπάθεια μείωσης ζήλιας με χρήση μη αποδοθέντων αγαθών)
  • Allocate remaining goods (απόδοση υπολοίπων με βάση safe sets)
  • Έλεγχο EFX (is_efx)
  • Συγκεντρωτική εκτέλεση/μέτρηση μετρικών (run_allocation)

"""
import random
import io
import sys
import copy
import time
from inputMethods import get_input
from inputMethods import get_input_from_edges, get_input_from_file

def greedy_allocation(agents, goods, valuations):
    """
    Greedy Allocation
    -----------------
    Δέχεται:
      • agents: λίστα πρακτόρων (κόμβοι του γράφου)
      • goods: λίστα "αγαθών" (ακμές, κάθε good είναι ζεύγος (u, v))
      • valuations: λεξικό {agent: {edge: value}} με τις αποτιμήσεις
    Επιστρέφει:
      • allocation: λεξικό {agent: good} με ΜΙΑ ακμή ανά πράκτορα (όπου επιλέχθηκε)

    Λογική:
      - Κρατά σύνολο αδιερεύνητων πρακτόρων N και αδιάθετα αγαθά M.
      - Επιλέγει πράκτορα i (από ουρά προτεραιότητας ή τυχαία από N).
      - Δίνει στον i την "καλύτερη" διαθέσιμη γειτονική ακμή (μέγιστη αποτίμηση).
      - Αντιστοίχως, προτεραιοποιεί τον «άλλο» κόμβο της ίδιας ακμής ώστε να επεξεργαστεί άμεσα.
    """
    N = set(agents)  # unprocessed agents
    M = set(goods)  # unallocated goods
    allocation = {}  # agent -> good
    queue = []  # priority queue for next check (προώθηση «γειτονικού» πράκτορα)

    print(f"Greedy Allocation")
    print(f"_____________________________________________________________________________")

    while N or queue:
        if queue:
            i = queue.pop(0)  # Εξυπηρέτηση πράκτορα από «ουρά προτεραιότητας»
        else:
            i = random.choice(list(N))  # Τυχαίος πράκτορας από N

        if i not in N:
            continue  # Ίσως επεξεργάστηκε ήδη ή έχει μετακινηθεί στην ουρά

        N.remove(i)
        if i in allocation:
            continue  # Έχει ήδη πάρει ακμή

        print("Agent:", i)

        # Βρες την καλύτερη διαθέσιμη γειτονική ακμή για τον i βάσει αποτίμησης v_i
        best_good = max(
            (e for e in M if e in goods and i in e),  # μόνο αδιάθετες και γειτονικές ακμές
            key=lambda e: valuations[i].get(e, 0),
            default=None
        )

        # Απόδοση ακμής και προτεραιοποίηση του άλλου άκρου
        if best_good:
            allocation[i] = best_good  # απόδωσε την ακμή στον i
            M.remove(best_good)  # διέγραψέ την από τα αδιάθετα
            print(f"  -> Gets {best_good} (value {valuations[i].get(best_good, 0)})")
            other = best_good[0] if best_good[1] == i else best_good[1]  # το «άλλο» άκρο της ακμής
            if other not in allocation and other in N:
                queue.insert(0, other)  # βάλε τον other μπροστά στην ουρά
    print(f"_____________________________________________________________________________")
    return allocation


def is_envied(agent, allocation, valuations):
    """
    Επιστρέφει True αν ΟΠΟΙΟΣΔΗΠΟΤΕ άλλος πράκτορας ζηλεύει τον 'agent'.
    Προσοχή: ο έλεγχος εδώ είναι «EF1-style» ως προς τον agent που ζηλεύεται:
      - Υπολογίζει για κάθε other αν προτιμά το bundle του agent από το δικό του.
    Χρησιμοποιείται ως «ένδειξη» ζήλιας στη ροή του αλγορίθμου.
    """
    Xi = allocation.get(agent, set())
    if not isinstance(Xi, set):
        Xi = {Xi}

    for other in valuations:
        if other == agent:
            continue

        Xj = allocation.get(other, set())
        if not isinstance(Xj, set):
            Xj = {Xj}

        # value_other_has: πώς αποτιμά ο other τα δικά του
        value_other_has = sum(valuations[other].get(g, 0) for g in Xj)
        # value_other_wants: πώς αποτιμά ο other το bundle του agent
        value_other_wants = sum(valuations[other].get(g, 0) for g in Xi)

        if value_other_wants > value_other_has:
            print(f"Agent {agent} is envied by {other} ({other} prefers {value_other_wants} > {value_other_has})")
            return True
    return False


def reduce_envy(allocation, valuations, goods):
    """
    Προσπάθεια μείωσης ζήλιας με χρήση αδιάθετων αγαθών.
    Βασική ιδέα:
      - Αν βρεθεί πράκτορας i που είναι ζηλευτός (κάποιος άλλος τον ζηλεύει),
        και το σύνολο Ui των αδιάθετων γειτονικών ακμών του i βελτιώνει την αξία του,
        τότε αντικαθιστούμε το τρέχον bundle του i με Ui (όπου είναι δυνατό).
      - Προσπαθούμε επίσης να μετακινήσουμε άλλους πράκτορες σε αδιάθετες ακμές που
        βελτιώνουν την κατάστασή τους.
    Τερματισμός όταν δεν αλλάζει τίποτα (changed == False).
    """
    print("Reduce Envy")
    print(f"_____________________________________________________________________________")
    # Κανονικοποίηση bundles σε σύνολα
    for agent in valuations:
        if agent not in allocation:
            allocation[agent] = set()
        elif not isinstance(allocation[agent], set):
            allocation[agent] = {allocation[agent]}

    all_goods = set(goods)
    allocated_goods = set(g for bundle in allocation.values() for g in bundle)
    unallocated_goods = all_goods - allocated_goods

    while True:
        changed = False
        for i in valuations:
            if not is_envied(i, allocation, valuations):
                continue

            # Ui: αδιάθετες γειτονικές ακμές του i
            Ui = [g for g in unallocated_goods if i in g]
            vi_Ui = sum(valuations[i].get(g, 0) for g in Ui)
            vi_Xi = sum(valuations[i].get(g, 0) for g in allocation.get(i, set()))

            # Αν το Ui βελτιώνει αξία για i, αντικατάσταση bundle
            if vi_Ui > vi_Xi:
                print(
                    f"\nAgent {i} is envied and prefers unallocated goods. Replacing X_i (value {vi_Xi}) with U_i(X) (value {vi_Ui})")
                print(f"  Old allocation: {allocation.get(i, set())}")
                print(f"  New allocation: {Ui}")
                # Επιστροφή παλιών αγαθών στα αδιάθετα
                for g in allocation.get(i, set()):
                    unallocated_goods.add(g)
                # Νέο bundle για i = Ui
                allocation[i] = set(Ui)
                for g in Ui:
                    unallocated_goods.remove(g)
                changed = True

                # Προσπάθεια βελτίωσης και για άλλους j με αδιάθετες ακμές
                for j in valuations:
                    if j == i:
                        continue
                    Uj = [g for g in unallocated_goods if j in g]
                    vj_Xj = sum(valuations[j].get(g, 0) for g in allocation.get(j, set()))
                    for g in Uj:
                        if valuations[j].get(g, 0) > vj_Xj:
                            print(f"  -> Agent {j} reallocated to {g} (value {valuations[j].get(g, 0)})")
                            for old in allocation.get(j, set()):
                                unallocated_goods.add(old)
                            allocation[j] = {g}
                            unallocated_goods.remove(g)
                            changed = True
                break

        if not changed:
            print("\nNo envy found with vi_Ui > vi_Xi. Terminating.\n")
            break

    # Επιστροφή σε «μονοστοιχείο» όπου ισχύει (αντί για set μεγέθους 1)
    for agent in allocation:
        if isinstance(allocation[agent], set) and len(allocation[agent]) == 1:
            allocation[agent] = list(allocation[agent])[0]

    print(f"_____________________________________________________________________________")

    return allocation


def get_safe_set(agent, allocation, valuations, unallocated_goods):
    """
    Υπολογισμός safe set για δοθέντα agent:
      - Υποψήφιοι είναι πράκτορες 'other' που ΔΕΝ είναι ζηλευτοί και
        ο agent, αξιολογώντας Xj ∪ Ui, δεν θα «υστερεί» σε αξία από το δικό του Xi.
      - Επιστρέφει σύνολο πρακτόρων που είναι «ασφαλείς» για ανάθεση υπολοίπων αγαθών.
    """
    safe_set = set()
    Xi = allocation.get(agent)
    if not isinstance(Xi, set):
        Xi = {Xi}
    vi_Xi = sum(valuations[agent].get(g, 0) for g in Xi)  # αξία τρέχοντος bundle του agent
    Ui = {g for g in unallocated_goods if agent in g}  # αδιάθετες γειτονικές ακμές του agent

    for other in allocation:
        if other == agent:
            continue
        Xj = allocation.get(other)
        if not isinstance(Xj, set):
            Xj = {Xj}
        Xj_union_Ui = Xj.union(Ui)
        vi_Xj_union_Ui = sum(valuations[agent].get(g, 0) for g in Xj_union_Ui)

        # Αν ο 'other' δεν είναι ζηλευτός ΚΑΙ ο agent δεν «χάνει» σε αξία έναντι Xj ∪ Ui,
        # τότε ο other είναι safe για τον agent
        if not is_envied(other, allocation, valuations):
            if vi_Xi >= vi_Xj_union_Ui:
                safe_set.add(other)

    return safe_set


def allocate_remaining_goods(allocation, goods, valuations):
    """
    Απόδοση των υπόλοιπων (αδιάθετων) ακμών:
      1) Αν ένας από τους δύο άκρους (a ή b) δεν είναι ζηλευτός, δώσε του την ακμή.
      2) Αν και οι δύο είναι ζηλευτοί, υπολόγισε τα safe sets και δώσε την ακμή
         σε τυχαίο «ασφαλή» πράκτορα από την τομή τους.
    Επιστρέφει:
      • νέο allocation
      • count unoriented (μετρητής περιπτώσεων «και οι δύο ζηλευτοί» που απαιτούν safe-set επιλογή)
    """
    unoriented_count = 0
    print(f"Allocate Remaining Goods")
    print(f"_____________________________________________________________________________")
    all_goods = set(goods)
    allocated_goods = set(
        g for bundle in allocation.values()
        for g in (bundle if isinstance(bundle, set) else {bundle})
    )
    unallocated_goods = all_goods - allocated_goods

    for good in list(unallocated_goods):
        a, b = good  # τα άκρα της ακμής

        # Έλεγχος αν οι άκρες είναι ζηλευτές στη τρέχουσα ανάθεση
        a_envied = is_envied(a, allocation, valuations)
        b_envied = is_envied(b, allocation, valuations)
        print(f"\n{good}:")
        print(f"  Agent {a} envied: {a_envied}")
        print(f"  Agent {b} envied: {b_envied}")

        if not a_envied:
            # Περίπτωση 1: δώσε στον a (μη ζηλευτό)
            allocation[a] = allocation.get(a, set()) | {good} if isinstance(allocation.get(a), set) else {
                allocation.get(a), good}
            print(f"Unallocated good {good} given to non-envied agent {a}")
            unallocated_goods.remove(good)
        elif not b_envied:
            # Περίπτωση 2: δώσε στον b (μη ζηλευτό)
            allocation[b] = allocation.get(b, set()) | {good} if isinstance(allocation.get(b), set) else {
                allocation.get(b), good}
            print(f"Unallocated good {good} given to non-envied agent {b}")
            unallocated_goods.remove(good)
        else:
            # Περίπτωση 3: και οι δύο ζηλευτοί → υπολογισμός safe sets & επιλογή από την τομή
            print(f"  [Safe Set Check] both agents envied")
            safe_a = get_safe_set(a, allocation, valuations, unallocated_goods)
            safe_b = get_safe_set(b, allocation, valuations, unallocated_goods)
            safe_agents = safe_a.intersection(safe_b)
            print(f"  Safe agents among {{'{a}', '{b}'}}: {safe_agents}")

            if safe_agents:
                unoriented_count += 1
                chosen_agent = random.choice(list(safe_agents))  # αυθαίρετη (τυχαία) επιλογή από safe agents
                allocation[chosen_agent] = allocation.get(chosen_agent, set()) | {good} if isinstance(
                    allocation.get(chosen_agent), set) else {allocation.get(chosen_agent), good}
                print(f"Unallocated good {good} given to safe agent {chosen_agent}")
                unallocated_goods.remove(good)
            else:
                # Ιδεατά δεν θα πρέπει να συμβεί (με βάση την θεωρία/ροή)
                print(f"  ERROR: No safe agent found (should not happen)")
    print(f"_____________________________________________________________________________")
    return allocation, unoriented_count


def is_efx(allocation, valuations, verbose=False, eps=1e-12):
    """
    Έλεγχος EFX:
      Για κάθε i != j και κάθε e ∈ Xj με v_i(e) > 0 ισχύει:
        v_i(X_i) >= v_i(X_j \ {e})
      Ισοδύναμα:
        v_i(X_i) >= v_i(X_j) - min_{e∈Xj, v_i(e)>0} v_i(e)
    Επιστρέφει (True/False, μήνυμα/log)
    """
    # Κανονικοποίηση bundles σε σύνολα
    bundles = {a: (set(B) if isinstance(B, set) else ({B} if B else set()))
               for a, B in allocation.items()}
    agents = list(bundles.keys())

    # Προϋπολογισμός v_i(X_i)
    vi_self = {i: sum(valuations[i].get(g, 0.0) for g in bundles[i]) for i in agents}
    log = []

    for i in agents:
        for j in agents:
            if i == j:
                continue
            Xj = bundles[j]
            if not Xj:
                continue
            # Υπολογισμός v_i(X_j) και του min^+ (ελάχιστο θετικό v_i(e))
            S = 0.0
            min_pos = None
            min_g = None
            for g in Xj:
                v = valuations[i].get(g, 0.0)
                S += v
                if v > eps and (min_pos is None or v < min_pos):
                    min_pos, min_g = v, g
            # Αν δεν υπάρχει αγαθό με θετική αξία για τον i στο Xj, η συνθήκη είναι τετριμμένη
            if min_pos is None:
                continue
            rhs = S - min_pos
            if rhs > vi_self[i] + eps:
                if verbose:
                    log.append(f"EFX violation (i={i}, j={j}): v_i(X_i)={vi_self[i]:.6f} "
                               f"< v_i(X_j)-min^+={rhs:.6f} (min at {min_g}={min_pos:.6f}, v_i(X_j)={S:.6f})")
                    return False, "\n".join(log)
                return False, (f"EFX violation for (i={i}, j={j}); best-removal for i is {min_g}")
    if verbose:
        log.append("✅ EFX holds.")
        return True, "\n".join(log)
    return True, "✅ EFX holds."


def run_allocation(agents, goods, valuations, show_details=False):
    """
    Κεντρική ροή εκτέλεσης:
      1) Greedy allocation
      2) Reduce Envy
      3) Allocate Remaining Goods
      + Μετρήσεις: χρόνος, envy ανά φάση, τελικό EFX, unoriented count, total/optimal/ratio.
    Αν show_details=True, επιστρέφει επιπλέον λεπτομερές log εκτύπωσης.
    """
    if show_details:
        buffer = io.StringIO()
        sys_stdout = sys.stdout
        sys.stdout = buffer

    start_t = time.perf_counter()

    total_agents = len(agents)

    # A1: Greedy
    greedy_alloc = greedy_allocation(agents, goods, valuations)
    envied_greedy = sum(1 for a in agents if is_envied(a, greedy_alloc, valuations))
    nonenvied_greedy = total_agents - envied_greedy
    pct_envied_greedy = (envied_greedy / total_agents * 100.0) if total_agents else 0.0
    pct_nonenvied_greedy = 100.0 - pct_envied_greedy

    # A2: Reduce Envy
    envy_reduced_input = copy.deepcopy(greedy_alloc)
    envy_reduced_alloc = reduce_envy(envy_reduced_input, valuations, goods)
    envied_reduce = sum(1 for a in agents if is_envied(a, envy_reduced_alloc, valuations))
    nonenvied_reduce = total_agents - envied_reduce
    pct_envied_reduce = (envied_reduce / total_agents * 100.0) if total_agents else 0.0
    pct_nonenvied_reduce = 100.0 - pct_envied_reduce

    # A3: Allocate Remaining
    before_final_alloc = copy.deepcopy(envy_reduced_alloc)
    final_alloc, unoriented_count = allocate_remaining_goods(before_final_alloc, goods, valuations)

    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    # EFX check (τελικός έλεγχος)
    efx_ok, efx_log = is_efx(final_alloc, valuations)
    print(efx_log)

    # --- Helper για bundle size ---
    def _bundle_size(b):
        if b is None:
            return 0
        if isinstance(b, set):
            return len(b)
        return 1

    # Πράκτορες χωρίς ακμές στο τέλος
    zero_edge_agents = sum(
        1 for a in agents
        if a not in final_alloc or _bundle_size(final_alloc.get(a)) == 0
    )
    pct_zero_edge = (zero_edge_agents / total_agents * 100.0) if total_agents else 0.0

    # Envied στο τέλος
    envied_final = sum(1 for a in agents if is_envied(a, final_alloc, valuations))
    nonenvied_final = total_agents - envied_final
    pct_envied_final = (envied_final / total_agents * 100.0) if total_agents else 0.0
    pct_nonenvied_final = 100.0 - pct_envied_final

    # --- Metrics text ---
    metrics_text = (
        "\n📊 Run Metrics\n"
        "────────────────────────────────────────────────────────\n"
        f"⏱️ Time elapsed: {elapsed_ms:.2f} ms\n"
        f"🕳️ Agents with no edge (final): {zero_edge_agents}/{total_agents} ({pct_zero_edge:.1f}%)\n\n"
        "😬 Envied agents per phase (count / % envied | % non-envied)\n"
        f"  • Greedy:       {envied_greedy}/{total_agents}  ({pct_envied_greedy:.1f}% | {pct_nonenvied_greedy:.1f}%)\n"
        f"  • Reduce Envy:  {envied_reduce}/{total_agents}  ({pct_envied_reduce:.1f}% | {pct_nonenvied_reduce:.1f}%)\n"
        f"  • Final:        {envied_final}/{total_agents}   ({pct_envied_final:.1f}% | {pct_nonenvied_final:.1f}%)\n"
    )

    # --- Τελική κατανομή & συνολική αξία ---
    final_text = metrics_text + "\n📦 Final Allocation:\n"
    total_value = 0
    for agent, bundle in final_alloc.items():
        if not isinstance(bundle, set):
            bundle = {bundle}
        value = sum(valuations.get(agent, {}).get(g, 0) for g in bundle)
        final_text += f"  {agent}: {bundle} (value: {value})\n"
        total_value += value

    # --- Optimal sum ---
    # Προσοχή: εδώ ο "βέλτιστος" ορίζεται ως άθροισμα max(v_u(e), v_v(e)) ανά ακμή e=(u,v),
    # δηλαδή η καλύτερη δυνατή «τοπική» ανάθεση ανά ακμή, ανεξάρτητα από παγκόσμιους περιορισμούς.
    optimal_sum = 0
    for e in goods:
        if not (isinstance(e, (tuple, list)) and len(e) == 2):
            continue
        u, v = e
        vu = valuations.get(u, {}).get(e, 0)
        vv = valuations.get(v, {}).get(e, 0)
        optimal_sum += max(vu, vv)

    ratio_vs_opt = (total_value / optimal_sum * 100.0) if optimal_sum else 0.0

    # --- Unoriented (count & %) ---
    total_goods = len(goods)
    pct_unoriented = (unoriented_count / total_goods * 100.0) if total_goods else 0.0

    final_text += (
        "\n🔎 Orientation & Optimality\n"
        "────────────────────────────────────────────────────────\n"
        f"🧮 Σύνολο αγαθών (edges): {total_goods}\n\n"
        f"🧭 Unoriented goods: {unoriented_count} / {total_goods}  ({pct_unoriented:.1f}%)\n\n"
        f"💰 Total value of allocation: {total_value}\n"
        f"🏁 Optimal sum (Σ max(u_i(e), u_j(e))): {optimal_sum}\n"
        f"📈 Αναλογία (Our/Optimal): {ratio_vs_opt:.1f}%\n"
    )

    if show_details:
        print(final_text)
        sys.stdout = sys_stdout
        return final_alloc, buffer.getvalue(), greedy_alloc, envy_reduced_alloc
    else:
        return final_alloc, final_text, greedy_alloc, envy_reduced_alloc
