import { useState } from 'react';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AIChatBanner } from '../components/AIChatBanner';
import { ChatWidget } from '../components/ChatWidget';
import { Calculator, PieChart as PieChartIcon } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

export function EMICalculator() {
  const [loanAmount, setLoanAmount] = useState(500000);
  const [interestRate, setInterestRate] = useState(10.5);
  const [tenureYears, setTenureYears] = useState(3);

  // Calculate EMI
  const calculateEMI = () => {
    const principal = loanAmount;
    const ratePerMonth = interestRate / 12 / 100;
    const tenureMonths = tenureYears * 12;

    if (ratePerMonth === 0) {
      return principal / tenureMonths;
    }

    const emi =
      (principal * ratePerMonth * Math.pow(1 + ratePerMonth, tenureMonths)) /
      (Math.pow(1 + ratePerMonth, tenureMonths) - 1);

    return Math.round(emi);
  };

  const emi = calculateEMI();
  const totalAmount = emi * tenureYears * 12;
  const totalInterest = totalAmount - loanAmount;

  const chartData = [
    { name: 'Principal Amount', value: loanAmount, color: '#004589' },
    { name: 'Total Interest', value: totalInterest, color: '#3B82F6' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <AIChatBanner />

      <div className="pt-24 pb-16 px-6">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <div className="inline-block bg-blue-100 p-4 rounded-full mb-4">
              <Calculator className="w-8 h-8 text-[#004589]" />
            </div>
            <h1 className="text-4xl text-gray-900 mb-4">EMI Calculator</h1>
            <p className="text-xl text-gray-600">
              Calculate your monthly installments instantly
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-8">
            {/* Left Side - Calculator */}
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-2xl text-gray-900 mb-6">Enter Loan Details</h2>

              {/* Loan Amount */}
              <div className="mb-8">
                <div className="flex justify-between mb-2">
                  <label className="text-gray-700">Loan Amount</label>
                  <span className="text-[#004589]">₹{loanAmount.toLocaleString('en-IN')}</span>
                </div>
                <input
                  type="range"
                  min="50000"
                  max="5000000"
                  step="10000"
                  value={loanAmount}
                  onChange={(e) => setLoanAmount(Number(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#004589]"
                />
                <div className="flex justify-between text-sm text-gray-500 mt-1">
                  <span>₹50K</span>
                  <span>₹50L</span>
                </div>
              </div>

              {/* Interest Rate */}
              <div className="mb-8">
                <div className="flex justify-between mb-2">
                  <label className="text-gray-700">Interest Rate (p.a.)</label>
                  <span className="text-[#004589]">{interestRate}%</span>
                </div>
                <input
                  type="range"
                  min="8"
                  max="20"
                  step="0.5"
                  value={interestRate}
                  onChange={(e) => setInterestRate(Number(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#004589]"
                />
                <div className="flex justify-between text-sm text-gray-500 mt-1">
                  <span>8%</span>
                  <span>20%</span>
                </div>
              </div>

              {/* Loan Tenure */}
              <div className="mb-8">
                <div className="flex justify-between mb-2">
                  <label className="text-gray-700">Loan Tenure</label>
                  <span className="text-[#004589]">{tenureYears} years</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="30"
                  step="1"
                  value={tenureYears}
                  onChange={(e) => setTenureYears(Number(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#004589]"
                />
                <div className="flex justify-between text-sm text-gray-500 mt-1">
                  <span>1 year</span>
                  <span>30 years</span>
                </div>
              </div>

              {/* Results */}
              <div className="bg-gradient-to-br from-[#004589] to-[#0066cc] rounded-xl p-6 text-white">
                <div className="text-center mb-4">
                  <div className="text-sm opacity-90 mb-1">Monthly EMI</div>
                  <div className="text-4xl">₹{emi.toLocaleString('en-IN')}</div>
                </div>
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/20">
                  <div className="text-center">
                    <div className="text-sm opacity-90 mb-1">Principal Amount</div>
                    <div className="text-lg">₹{loanAmount.toLocaleString('en-IN')}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm opacity-90 mb-1">Total Interest</div>
                    <div className="text-lg">₹{totalInterest.toLocaleString('en-IN')}</div>
                  </div>
                </div>
                <div className="text-center mt-4 pt-4 border-t border-white/20">
                  <div className="text-sm opacity-90 mb-1">Total Amount Payable</div>
                  <div className="text-2xl">₹{totalAmount.toLocaleString('en-IN')}</div>
                </div>
              </div>
            </div>

            {/* Right Side - Chart & Info */}
            <div>
              {/* Pie Chart */}
              <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
                <h2 className="text-2xl text-gray-900 mb-6">Payment Breakdown</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={chartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => `₹${value.toLocaleString('en-IN')}`} />
                  </PieChart>
                </ResponsiveContainer>

                <div className="mt-6 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-[#004589] rounded"></div>
                      <span className="text-gray-700">Principal Amount</span>
                    </div>
                    <span className="text-gray-900">₹{loanAmount.toLocaleString('en-IN')}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-[#3B82F6] rounded"></div>
                      <span className="text-gray-700">Total Interest</span>
                    </div>
                    <span className="text-gray-900">₹{totalInterest.toLocaleString('en-IN')}</span>
                  </div>
                </div>
              </div>

              {/* Quick Tips */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-8 border border-blue-100">
                <h3 className="text-xl text-gray-900 mb-4">💡 Pro Tips</h3>
                <ul className="space-y-3 text-gray-700">
                  <li>• Higher down payment reduces your EMI burden</li>
                  <li>• Shorter tenure means less interest paid overall</li>
                  <li>• Check your credit score before applying</li>
                  <li>• Compare rates from different lenders</li>
                  <li>• Pre-closure charges may apply</li>
                </ul>
              </div>
            </div>
          </div>

          {/* CTA */}
          <div className="mt-12 bg-white rounded-xl shadow-lg p-8 text-center">
            <h2 className="text-2xl text-gray-900 mb-4">
              Ready to Apply for Your Loan?
            </h2>
            <p className="text-gray-600 mb-6">
              Get instant approval with our AI-powered loan assistant
            </p>
            <button className="bg-[#004589] text-white px-8 py-3 rounded-lg hover:bg-[#003366] transition-colors">
              Apply Now
            </button>
          </div>
        </div>
      </div>

      <Footer />
      <ChatWidget />
    </div>
  );
}