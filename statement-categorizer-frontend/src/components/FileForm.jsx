import { useState } from 'react';
import { useFilePicker } from 'use-file-picker';

export default function FileForm() {
    const { openFilePicker, filesContent, plainFiles, loading } = useFilePicker({
        accept: '.pdf',
        multiple: false,
    });

    const [transactions, setTransactions] = useState([]);
    const [isParsing, setIsParsing] = useState(false);

    if (loading) {
        return <div>Loading...</div>;
    }

    const selectedFile = filesContent[0];

    const handleUpload = async () => {
        if (!plainFiles || plainFiles.length === 0) {
            alert('Please select a PDF file first.');
            return;
        }

        const formData = new FormData();
        formData.append('file', plainFiles[0]);

        try {
            setIsParsing(true);
            const response = await fetch('http://192.168.1.5:8000/parse-statement', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Server returned an error response.');
            }

            const result = await response.json();
            setTransactions(result || []);
        } catch (error) {
            console.error('Failed to upload file:', error);
        } finally {
            setIsParsing(false);
        }
    };

    return (
        <div className="p-4">
            <div className='flex justify-center m-2 gap-2'>
                <div>
                    <button className='bg-amber-950 text-white p-2' id='file_picker_btn' onClick={() => openFilePicker()}>
                        Upload Bank Statement
                    </button>
                    {selectedFile && (
                        <div>
                            <h2>{selectedFile.name}</h2>
                        </div>
                    )}
                </div>
                <button className="bg-green-700 p-2 h-10 text-white" onClick={handleUpload}>
                    {isParsing ? 'Parsing...' : 'Parse PDF'}
                </button>
            </div>
            <br />
            {transactions.length > 0 && (
                <table className="min-w-full border-collapse border border-gray-300 mt-4">
                    <thead>
                        <tr className="bg-gray-100">
                            <th className="border border-gray-300 p-2">Description</th>
                            <th className="border border-gray-300 p-2">Amount</th>
                            <th className="border border-gray-300 p-2">Category</th>
                        </tr>
                    </thead>
                    <tbody>
                        {transactions.map((tx, index) => (
                            <tr key={index}>
                                <td className="border border-gray-300 p-2">{tx.description}</td>
                                <td className="border border-gray-300 p-2">{tx.amount}</td>
                                <td className="border border-gray-300 p-2">{tx.category}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
}