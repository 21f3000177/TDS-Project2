# /// script
# dependencies = [
#   "python-dotenv",
#   "requests",
#   "pandas",
#   "numpy",
#   "seaborn",
#   "matplotlib",
#   "openai==0.28",
#   "scikit-learn",
#   "requests",
# ]
# ///

import os
import pandas as pd
import argparse
import openai
import requests
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = os.getenv('AIPROXY_TOKEN')
openai.api_key = AIPROXY_TOKEN


def append_to_readme(output_folder, heading=None, content=None):
    """Append an image with a heading to the README.md file."""
    readme_path = os.path.join(output_folder, "README.md")
    with open(readme_path, "a") as readme_file:
        if heading:
            readme_file.write(f"\n## {heading}\n")
        if content:
            readme_file.write(f"\n {content}\n")
    return


def append_img_to_readme(output_folder, heading, image_path):
    """Append an image with a heading to the README.md file."""
    readme_path = os.path.join(output_folder, "README.md")
    with open(readme_path, "a") as readme_file:
        readme_file.write(f"\n### {heading}\n")
        readme_file.write(f"![{heading}]({os.path.basename(image_path)})\n")
    return


def visualize_data(data, output_folder):
    """Generate and save various visualizations for the dataset."""
    # Generate histograms for numeric data
    numeric_data = data.select_dtypes(include=['float'])
    if not numeric_data.empty:
        test_data_h = numeric_data.columns[:1] if len(numeric_data.columns) > 2 else numeric_data.columns
        for column in test_data_h:
            plt.figure()
            sns.histplot(data[column].dropna(), kde=True, bins=30, color='blue')
            plt.title(f'Histogram of {column}')
            plt.xlabel(column)
            plt.ylabel('Frequency')
            histogram_path = os.path.join(output_folder, f"histogram_{column}.png")
            plt.savefig(histogram_path)
            plt.close()
            append_img_to_readme(output_folder, f"Histogram of {column}", histogram_path)

    numeric_data = data.select_dtypes(include=['integer'])
    test_data_bp = numeric_data.columns[-1:] if len(numeric_data.columns) > 2 else numeric_data.columns
    # Generate box plots for numeric data
    for column in test_data_bp:
        plt.figure()
        sns.boxplot(x=data[column].dropna(), color='green')
        plt.title(f'Box Plot of {column}')
        plt.xlabel(column)
        boxplot_path = os.path.join(output_folder, f"boxplot_{column}.png")
        plt.savefig(boxplot_path)
        plt.close()
        # append_img_to_readme(output_folder, f"Box Plot of {column}", boxplot_path)


def generate_summary(data):
    """
    Generate a summary of the dataset including missing values, duplicates, correlations, and outliers.
    :param data:
    :return:
    """
    summary = []

    # Dataset overview
    summary.append(f"Dataset contains {data.shape[0]} rows and {data.shape[1]} columns.")

    # Missing values
    missing_values = data.isnull().sum()
    missing_summary = missing_values[missing_values > 0]
    if not missing_summary.empty:
        summary.append(f"Missing values detected in {len(missing_summary)} columns.")
    else:
        summary.append("No missing values detected.")

    # Duplicate rows
    duplicate_count = data.duplicated().sum()
    summary.append(f"Dataset contains {duplicate_count} duplicate rows.")

    # Correlation matrix
    numeric_data = data.select_dtypes(include=['number'])
    if not numeric_data.empty:
        correlation_matrix = numeric_data.corr()
        strong_correlations = correlation_matrix[(correlation_matrix.abs() > 0.8) & (correlation_matrix.abs() < 1)]
        if not strong_correlations.empty:
            summary.append("Strong correlations detected among numeric features.")
        else:
            summary.append("No strong correlations detected among numeric features.")
    else:
        summary.append("No numeric columns available for correlation analysis.")

    # Outlier detection
    outlier_counts = {}
    for column in numeric_data.columns:
        Q1 = numeric_data[column].quantile(0.25)
        Q3 = numeric_data[column].quantile(0.75)
        IQR = Q3 - Q1
        outliers = ((numeric_data[column] < (Q1 - 1.5 * IQR)) | (numeric_data[column] > (Q3 + 1.5 * IQR))).sum()
        outlier_counts[column] = outliers
    total_outliers = sum(outlier_counts.values())
    summary.append(f"Detected {total_outliers} potential outliers across numeric columns.")

    return "\n".join(summary)


def create_out_dir(file_path):
    """Create a folder named after the CSV file (excluding extension) and add a README.md file."""
    # Extract file name without extension
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    folder_path = os.path.join(os.getcwd(), file_name)

    # Create folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Create a README.md file
    readme_path = os.path.join(folder_path, "README.md")
    return folder_path


def generate_story(file_name, summary):
    """
    Generate a story using the AI Proxy API.
    :param file_name: csv file name
    :param summary: findings after analysing the dataset
    :return:
    """
    # Define headers for the request, including authorization and content type
    headers = {
        "Authorization": f"Bearer {AIPROXY_TOKEN}",
        "Content-Type": "application/json"
    }
    prompt = f"Write a detailed report on the analysis of the dataset '{file_name}'.\n\nAnalysis report:\n{summary}\n\nInclude insights, observations, and possible implications."
    # Request payload
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt},
        ]
    }
    response = requests.post(API_URL, headers=headers, json=payload)

    # Check the response
    if response.status_code == 200:
        data = response.json()
        return data.get('choices', [{}])[0].get('message', {}).get('content', 'No response from model')
    else:
        return f"Error {response.status_code}: {response.text}"


def analyze_csv(file_path, output_folder):
    try:
        findings = {}
        relevant_charts = {}
        # Load the dataset
        try:
            data = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            print("UTF-8 decoding failed. Trying 'ISO-8859-1' encoding...")
            data = pd.read_csv(file_path, encoding='ISO-8859-1')

        findings['rows'] = data.shape[0]
        findings['columns'] = data.shape[1]
        findings['column_info'] = data.info()
        findings['summary_stats'] = data.describe(include='all')
        missing_values = data.isnull().sum()
        findings['missing_values'] = missing_values[missing_values > 0]
        findings['top_5_rows'] = data.head()
        findings['data_types'] = data.dtypes
        summary = generate_summary(data)
        # Detect duplicates
        duplicate_count = data.duplicated().sum()
        findings['duplicates'] = duplicate_count

        # Correlation Matrix
        numeric_data = data.select_dtypes(include=['number'])
        if not numeric_data.empty:
            correlation_matrix = numeric_data.corr()

            # Plot Correlation Heatmap
            plt.figure(figsize=(10, 8))
            sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm')
            plt.title('Correlation Heatmap')
            heatmap_path = os.path.join(output_folder, "correlation_heatmap.png")
            plt.savefig(heatmap_path)
            relevant_charts["Correlation Heatmap"] = heatmap_path
            findings['correlation_matrix'] = correlation_matrix

        # Outlier Detection (using IQR)
        outlier_counts = {}
        for column in numeric_data.columns:
            Q1 = numeric_data[column].quantile(0.25)
            Q3 = numeric_data[column].quantile(0.75)
            IQR = Q3 - Q1
            outliers = ((numeric_data[column] < (Q1 - 1.5 * IQR)) | (numeric_data[column] > (Q3 + 1.5 * IQR))).sum()
            #print(f"{column}: {outliers} outliers")
            if outliers > 0:
                outlier_counts[column] = outliers
        findings['outlier_per_column'] = outlier_counts

        if not numeric_data.empty:
            kmeans = KMeans(n_clusters=2, random_state=0)
            numeric_data = numeric_data.fillna(numeric_data.mean())
            data['Cluster'] = kmeans.fit_predict(numeric_data)
            #print(data[['Cluster']].value_counts())

            # Plot clustering results
            plt.figure(figsize=(8, 6))
            plt.scatter(numeric_data.iloc[:, 0], numeric_data.iloc[:, 1], c=data['Cluster'], cmap='viridis')
            plt.title('KMeans Clustering')
            plt.xlabel(numeric_data.columns[0])
            plt.ylabel(numeric_data.columns[1])
            clustering_path = os.path.join(output_folder, "kmeans_clustering.png")
            plt.savefig(clustering_path)
            #print(f"KMeans clustering plot saved to {clustering_path}")
            findings['kmeans_clusters'] = data['Cluster'].value_counts()
            relevant_charts["KMeans Clustering Plot"] = clustering_path


        # Generate story
        file_name = os.path.basename(file_path)
        story = generate_story(file_name, findings)
        append_to_readme(output_folder,content=story)
        # Add relevant chart for readme
        append_to_readme(output_folder, heading="Visualizations")
        for key,value in relevant_charts.items():
            append_img_to_readme(output_folder, key, value)

        visualize_data(data, output_folder)
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
    except pd.errors.EmptyDataError:
        print(f"Error: File is empty - {file_path}")
    except pd.errors.ParserError:
        print(f"Error: File could not be parsed - {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return


def main():
    parser = argparse.ArgumentParser(description="Analyze a CSV file.")
    parser.add_argument("file", help="Path to the CSV file to analyze.")
    args = parser.parse_args()

    # Create output folder and README
    curr_path = create_out_dir(args.file)
    analyze_csv(args.file, curr_path)


if __name__ == "__main__":
    main()
