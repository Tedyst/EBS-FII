import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


data = pd.read_csv('results_Vlad.csv')


sns.set(style="whitegrid")




plt.figure(figsize=(10, 6))
sns.lineplot(x="Publications", y="Execution Time", data=data, hue="Threads", marker="o")
plt.title('Timpul de execuție în funcție de numărul de publicații')
plt.xlabel('Număr publicații')
plt.ylabel('Timp de execuție (secunde)')
plt.legend(title="Threads")

plt.savefig('graphs//Vlad//publications_execution_time.png')


plt.figure(figsize=(10, 6))
sns.lineplot(x="Subscriptions", y="Execution Time", data=data, hue="Threads", marker="o")
plt.title('Timpul de execuție în funcție de numărul de abonamente')
plt.xlabel('Număr abonamente')
plt.ylabel('Timp de execuție (secunde)')
plt.legend(title="Threads")

plt.savefig('graphs//Vlad//subscriptions_execution_time.png')


plt.figure(figsize=(10, 6))
sns.lineplot(x="Processes", y="Execution Time", data=data, hue="Threads", marker="o")
plt.title('Timpul de execuție în funcție de numărul de procese')
plt.xlabel('Număr procese')
plt.ylabel('Timp de execuție (secunde)')
plt.legend(title="Threads")

plt.savefig('graphs//Vlad//processes_execution_time.png')


plt.figure(figsize=(10, 6))
sns.lineplot(x="Threads", y="Execution Time", data=data, hue="Processes", marker="o")
plt.title('Timpul de execuție în funcție de numărul de threaduri')
plt.xlabel('Număr threaduri')
plt.ylabel('Timp de execuție (secunde)')
plt.legend(title="Procese")

plt.savefig('graphs//Vlad//threads_execution_time.png')

