# inputMethods.py
def get_input():
    print("=== EFX Allocation Input Interface ===")
    agents = input("Enter agent names (comma-separated, e.g. A,B,C): ").split(',')
    agents = [a.strip() for a in agents]

    num_goods = int(input("Enter number of goods (edges): "))
    goods = []
    for i in range(num_goods):
        edge = input(f"Enter endpoints of good {i+1} (format: A,B): ")
        a, b = edge.strip().split(',')
        goods.append((a.strip(), b.strip()))

    valuations = {}
    for agent in agents:
        print(f"\nEnter valuations for agent {agent} (only for relevant goods):")
        valuations[agent] = {}
        for good in goods:
            if agent in good:  # Only prompt for relevant goods
                val = input(f"  Value of {good}: ")
                try:
                    val = int(val)
                except ValueError:
                    val = 0
                valuations[agent][good] = val

    return agents, goods, valuations



def get_input_from_edges():
    print("=== EFX Allocation Input from Edge Valuations ===")
    print("Enter edges with valuations in the format 'A,B:valA,valB'. Type 'done' to finish.")

    agents = set()
    goods = []
    valuations = {}
    entered_edges = set()

    while True:
        line = input("Enter edge and valuations: ").strip()
        if line.lower() == 'done':
            break

        try:
            pair_part, val_part = line.split(':')
            a, b = pair_part.strip().split(',')
            valA, valB = map(int, val_part.strip().split(','))
            edge = tuple(sorted((a.strip(), b.strip())))
        except Exception as e:
            print("  Invalid format. Please use 'A,B:valA,valB'.")
            continue

        # Detect multigraph condition
        if edge in entered_edges or (len(goods) + 1) > ((len(agents.union({a, b})) * (len(agents.union({a, b})) - 1)) // 2):
            print("  ❌ This edge would make the graph a multigraph. It will not be added.")
            continue

        entered_edges.add(edge)
        goods.append(edge)
        agents.update([a, b])

        for agent, val in zip([a, b], [valA, valB]):
            if agent not in valuations:
                valuations[agent] = {}
            valuations[agent][edge] = val

    agents = list(agents)
    return agents, goods, valuations

def get_input_from_file(filename):
    agents = set()
    goods = []
    valuations = {}

    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if not line or ':' not in line:
                continue

            # Split into "A,B" and "valA,valB"
            try:
                pair_part, value_part = line.split(':')
                ends = pair_part.split(',')
                values = value_part.split(',')

                if len(ends) != 2 or len(values) != 2:
                    print(f"⚠️ Skipping invalid line: {line}")
                    continue

                a, b = ends[0].strip(), ends[1].strip()
                val_a, val_b = int(values[0].strip()), int(values[1].strip())

                good = (a, b)
                goods.append(good)
                agents.update([a, b])

                if a not in valuations:
                    valuations[a] = {}
                if b not in valuations:
                    valuations[b] = {}

                valuations[a][good] = val_a
                valuations[b][good] = val_b

            except Exception as e:
                print(f"❌ Error parsing line: {line} → {e}")
                continue

    return list(agents), goods, valuations


