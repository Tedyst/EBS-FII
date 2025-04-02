import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Încarcă datele CSV într-un DataFrame
data = pd.read_csv('results.csv')

# Configurează stilul graficului
sns.set(style="whitegrid")

# Grafice pentru a compara timpul de execuție în funcție de fiecare parametru

# Grafic pentru Publications vs. Execution Time
plt.figure(figsize=(10, 6))
sns.lineplot(x="Publications", y="Execution Time", data=data, hue="Threads", marker="o")
plt.title('Timpul de execuție în funcție de numărul de publicații')
plt.xlabel('Număr publicații')
plt.ylabel('Timp de execuție (secunde)')
plt.legend(title="Threads")
plt.show()

# Grafic pentru Subscriptions vs. Execution Time
plt.figure(figsize=(10, 6))
sns.lineplot(x="Subscriptions", y="Execution Time", data=data, hue="Threads", marker="o")
plt.title('Timpul de execuție în funcție de numărul de abonamente')
plt.xlabel('Număr abonamente')
plt.ylabel('Timp de execuție (secunde)')
plt.legend(title="Threads")
plt.show()

# Grafic pentru Processes vs. Execution Time
plt.figure(figsize=(10, 6))
sns.lineplot(x="Processes", y="Execution Time", data=data, hue="Threads", marker="o")
plt.title('Timpul de execuție în funcție de numărul de procese')
plt.xlabel('Număr procese')
plt.ylabel('Timp de execuție (secunde)')
plt.legend(title="Threads")
plt.show()

# Grafic pentru Threads vs. Execution Time
plt.figure(figsize=(10, 6))
sns.lineplot(x="Threads", y="Execution Time", data=data, hue="Processes", marker="o")
plt.title('Timpul de execuție în funcție de numărul de threaduri')
plt.xlabel('Număr threaduri')
plt.ylabel('Timp de execuție (secunde)')
plt.legend(title="Procese")
plt.show()
